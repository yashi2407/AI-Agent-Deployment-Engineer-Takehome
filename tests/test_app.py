"""Offline contract tests: no credentials or paid model calls required."""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.schemas import StoryRequest
from backend.llm import MODEL, StoryUnavailable
from backend.storyteller import generate_story

@pytest.fixture(autouse=True)
def default_provider(monkeypatch):
    monkeypatch.setenv('STORY_PROVIDER', 'claude')


STORY = {'title': 'The Little Star', 'story': ' '.join(['gentle'] * 240)}
GOOD = {'safe': True, 'scores': {k: 4 for k in
        ['age_fit', 'story_arc', 'warmth', 'bedtime', 'request_fit']}, 'feedback': 'A cozy complete tale.'}

def fake_client(*outputs):
    client = Mock()
    client.messages.create.side_effect = [SimpleNamespace(stop_reason='end_turn', content=[
        SimpleNamespace(type='text', text=json.dumps(item))]) for item in outputs]
    return client

def test_first_draft_passes_and_model_preserved():
    client = fake_client(STORY, GOOD)
    result = generate_story(StoryRequest(prompt='A gentle fox'), client)
    assert result['revisions'] == 0
    assert result['reviews'][0]['approved'] is True
    assert all(c.kwargs['model'] == MODEL == 'claude-haiku-5-5'
               for c in client.messages.create.call_args_list)

def test_feedback_reaches_writer_and_revision_is_rejudged():
    bad = {**GOOD, 'scores': {**GOOD['scores'], 'bedtime': 2}, 'feedback': 'Add a calming ending.'}
    client = fake_client(STORY, bad, STORY, GOOD)
    result = generate_story(StoryRequest(prompt='A gentle fox'), client)
    assert result['revisions'] == 1
    assert len(result['reviews']) == 2
    revision_data = json.loads(client.messages.create.call_args_list[2].kwargs['messages'][0]['content'])
    assert revision_data['review']['feedback'] == bad['feedback']

@pytest.mark.parametrize('review,story', [({**GOOD, 'safe': False}, STORY),
    ({**GOOD, 'scores': {**GOOD['scores'], 'age_fit': 2}}, STORY),
    (GOOD, {**STORY, 'story': ' '.join(['short'] * 20)})])
def test_rejected_drafts_never_return_and_budget_is_bounded(review, story):
    client = fake_client(*([story, review] * 3))
    with pytest.raises(StoryUnavailable):
        generate_story(StoryRequest(prompt='A gentle fox'), client)
    assert client.messages.create.call_count == 6

@pytest.mark.parametrize('review', [{**GOOD, 'safe': 'false'},
    {**GOOD, 'scores': {**GOOD['scores'], 'age_fit': 9}}])
def test_malformed_judge_cannot_approve(review):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        generate_story(StoryRequest(prompt='A gentle fox'), fake_client(STORY, review))

def test_truncated_output_is_rejected():
    client = fake_client()
    client.messages.create.side_effect = None
    client.messages.create.return_value = SimpleNamespace(stop_reason='max_tokens', content=[
        SimpleNamespace(type='text', text='{}')])
    with pytest.raises(StoryUnavailable):
        generate_story(StoryRequest(prompt='A gentle fox'), client)

web = TestClient(app)

@pytest.mark.parametrize('body', [{'prompt': '   '}, {'prompt': 'fox', 'age': 11},
    {'prompt': 'fox', 'age': True}, {'prompt': 'x' * 1201},
    {'prompt': 'fox', 'length': 'forever'}])
def test_validation_precedes_generation(body):
    with patch('backend.app.generate_story') as generate:
        assert web.post('/api/stories', json=body).status_code == 422
        generate.assert_not_called()

def test_home_assets_and_health():
    assert web.get('/').status_code == 200
    assert web.get('/static/app.js').status_code == 200
    assert web.get('/static/style.css').status_code == 200
    assert web.get('/api/health').json()['status'] == 'ok'

def test_success_api_contract():
    with patch('backend.app.generate_story', return_value={**STORY, 'revisions': 0}):
        response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
        assert response.status_code == 200
        assert response.json()['title'] == STORY['title']

def test_failure_does_not_leak_draft():
    with patch('backend.app.generate_story', side_effect=StoryUnavailable('Try another idea.')):
        response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
        assert response.status_code == 503
        assert 'story' not in response.json()

def test_missing_key_is_actionable(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
    assert response.status_code == 503
    assert 'ANTHROPIC_API_KEY' in response.json()['detail']


def test_anthropic_sdk_request_and_response():
    """Exercise the actual SDK against a local mock HTTP transport."""
    import httpx
    from anthropic import Anthropic
    from backend.prompts import STORY_PROMPT
    from backend.llm import call_model

    def respond(request):
        payload = json.loads(request.content)
        assert request.url.path == '/v1/messages'
        assert payload['model'] == 'claude-haiku-5-5'
        assert payload['system'] == STORY_PROMPT
        assert payload['messages'][0]['role'] == 'user'
        assert json.loads(payload['messages'][0]['content'])['prompt'] == 'A gentle fox'
        assert 'response_format' not in payload
        return httpx.Response(200, json={
            'id': 'msg_test', 'type': 'message', 'role': 'assistant', 'model': MODEL,
            'content': [{'type': 'text', 'text': json.dumps(STORY)}],
            'stop_reason': 'end_turn', 'stop_sequence': None,
            'usage': {'input_tokens': 10, 'output_tokens': 20},
        })

    with Anthropic(api_key='test-key', http_client=httpx.Client(
            transport=httpx.MockTransport(respond))) as client:
        assert call_model(client, STORY_PROMPT, {'prompt': 'A gentle fox'}) == STORY


def test_provider_error_returns_generic_message():
    from anthropic import APIConnectionError
    import httpx
    error = APIConnectionError(request=httpx.Request('POST', 'https://api.anthropic.com/v1/messages'))
    with patch('backend.app.generate_story', side_effect=error):
        response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
        assert response.status_code == 502
        assert 'story' not in response.json()


def test_invalid_json_is_not_displayed():
    with patch('backend.app.generate_story', side_effect=json.JSONDecodeError('Invalid', 'x', 0)):
        response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
        assert response.status_code == 502
        assert 'story' not in response.json()


def fake_gemini_client(*outputs):
    client = Mock()
    client.models.generate_content.side_effect = [SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason='STOP')], text=json.dumps(item)
    ) for item in outputs]
    return client


def test_gemini_generation_and_revision():
    bad = {**GOOD, 'scores': {**GOOD['scores'], 'bedtime': 2}}
    client = fake_gemini_client(STORY, bad, STORY, GOOD)
    result = generate_story(StoryRequest(prompt='A gentle fox'), client, provider='gemini')
    assert result['model'] == 'gemini-2.5-flash-lite'
    assert result['revisions'] == 1
    assert client.models.generate_content.call_count == 4
    for call in client.models.generate_content.call_args_list:
        assert call.kwargs['model'] == 'gemini-2.5-flash-lite'
        assert call.kwargs['config'].response_mime_type == 'application/json'
        assert call.kwargs['config'].system_instruction
    client.messages.create.assert_not_called()


@pytest.mark.parametrize('reason', ['MAX_TOKENS', 'SAFETY'])
def test_gemini_interrupted_or_blocked_output(reason):
    from backend.llm import call_model
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason=reason)], text=json.dumps(STORY))
    with pytest.raises(StoryUnavailable):
        call_model(client, 'Return JSON', {}, 'gemini')


def test_gemini_missing_key_and_health(monkeypatch):
    monkeypatch.setenv('STORY_PROVIDER', 'gemini')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    health = web.get('/api/health').json()
    assert health['provider'] == 'gemini'
    assert health['configured'] is False
    response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
    assert response.status_code == 503
    assert 'GEMINI_API_KEY' in response.json()['detail']


def test_invalid_provider_is_actionable(monkeypatch):
    monkeypatch.setenv('STORY_PROVIDER', 'unknown')
    response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
    assert response.status_code == 503
    assert 'STORY_PROVIDER' in response.json()['detail']


def test_gemini_provider_error_is_handled():
    from google.genai.errors import ClientError
    with patch('backend.app.generate_story', side_effect=ClientError(429, {'error': {'message': 'Quota exhausted'}})):
        response = web.post('/api/stories', json={'prompt': 'A gentle fox'})
        assert response.status_code == 502


def test_gemini_sdk_request_and_response():
    import httpx
    from google import genai
    from google.genai import types
    from backend.llm import call_model
    from backend.prompts import STORY_PROMPT

    def respond(request):
        assert request.url.path.endswith('/models/gemini-2.5-flash-lite:generateContent')
        payload = json.loads(request.content)
        assert payload['systemInstruction']['parts'][0]['text'] == STORY_PROMPT
        assert payload['generationConfig']['responseMimeType'] == 'application/json'
        assert json.loads(payload['contents'][0]['parts'][0]['text'])['prompt'] == 'A gentle fox'
        return httpx.Response(200, json={'candidates': [{
            'content': {'role': 'model', 'parts': [{'text': json.dumps(STORY)}]},
            'finishReason': 'STOP',
        }]})

    with genai.Client(api_key='test-key', vertexai=False, http_options=types.HttpOptions(
            client_args={'transport': httpx.MockTransport(respond)})) as client:
        assert call_model(client, STORY_PROMPT, {'prompt': 'A gentle fox'}, 'gemini') == STORY


@pytest.mark.parametrize('provider', ['claude', 'gemini'])
def test_user_feedback_reaches_writer_and_judge_through_revisions(provider):
    request = StoryRequest(prompt='A gentle fox', age=6, feedback='Add a bunny friend.',
                           previous_story=STORY)
    bad = {**GOOD, 'scores': {**GOOD['scores'], 'request_fit': 2},
           'feedback': 'Include the requested bunny.'}
    client = (fake_client if provider == 'claude' else fake_gemini_client)(STORY, bad, STORY, GOOD)
    result = generate_story(request, client, provider)
    assert result['revisions'] == 1
    calls = (client.messages.create if provider == 'claude'
             else client.models.generate_content).call_args_list
    for call in calls:
        payload = json.loads(call.kwargs['messages'][0]['content'] if provider == 'claude'
                             else call.kwargs['contents'])
        assert payload['feedback'] == request.feedback
        assert payload['age'] == 6
        assert payload['previous_story'] == STORY
    second_draft = json.loads(calls[2].kwargs['messages'][0]['content'] if provider == 'claude'
                              else calls[2].kwargs['contents'])
    assert second_draft['review']['feedback'] == bad['feedback']


@pytest.mark.parametrize('extra', [
    {'feedback': '   ', 'previous_story': STORY},
    {'feedback': 'x' * 1201, 'previous_story': STORY},
    {'feedback': 'Add a bunny.'},
    {'previous_story': STORY},
    {'feedback': 'Add a bunny.', 'previous_story': {'title': 'Fox', 'story': 'Too short'}},
])
def test_invalid_user_feedback_is_rejected_before_model_call(extra):
    with patch('backend.app.generate_story') as generate:
        response = web.post('/api/stories', json={'prompt': 'A gentle fox', **extra})
        assert response.status_code == 422
        generate.assert_not_called()


def test_feedback_api_passes_previous_story_and_trimmed_feedback():
    with patch('backend.app.generate_story', return_value=STORY) as generate:
        response = web.post('/api/stories', json={
            'prompt': 'A gentle fox', 'feedback': '  Add a bunny friend.  ',
            'previous_story': STORY})
        assert response.status_code == 200
        request = generate.call_args.args[0]
        assert request.feedback == 'Add a bunny friend.'
        assert request.previous_story.model_dump() == STORY
