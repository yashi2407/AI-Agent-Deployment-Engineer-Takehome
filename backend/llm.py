"""Provider calls: Claude for submission, Gemini for local testing."""
import json
import os

from anthropic import Anthropic
from google import genai
from google.genai import types

MODEL = 'claude-haiku-5-5'
PROVIDERS = {
    'claude': (MODEL, 'ANTHROPIC_API_KEY'),
    'gemini': ('gemini-2.5-flash-lite', 'GEMINI_API_KEY'),
}


class StoryUnavailable(Exception):
    pass


def selected_provider():
    provider = os.getenv('STORY_PROVIDER', 'claude').strip().lower()
    if provider not in PROVIDERS:
        raise StoryUnavailable('Set STORY_PROVIDER to claude or gemini in .env.')
    return provider


def create_client(provider):
    _, key_name = PROVIDERS[provider]
    key = os.getenv(key_name)
    if not key:
        raise StoryUnavailable(f'Add {key_name} to .env, then restart the app.')
    if provider == 'gemini':
        return genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(
            timeout=40000, retry_options=types.HttpRetryOptions(attempts=1)))
    return Anthropic(api_key=key, timeout=40.0, max_retries=0)


def call_model(client, system, data, provider='claude'):
    model, _ = PROVIDERS[provider]
    if provider == 'gemini':
        response = client.models.generate_content(
            model=model, contents=json.dumps(data),
            config=types.GenerateContentConfig(
                system_instruction=system, response_mime_type='application/json',
                max_output_tokens=2200),
        )
        if not response.candidates or response.candidates[0].finish_reason != types.FinishReason.STOP:
            raise StoryUnavailable('The story was interrupted or blocked. Please try another idea.')
        text = response.text
    else:
        response = client.messages.create(
            model=model, system=system,
            messages=[{'role': 'user', 'content': json.dumps(data)}], max_tokens=2200,
        )
        if response.stop_reason != 'end_turn':
            raise StoryUnavailable('The story was interrupted. Please try again.')
        text = ''.join(block.text for block in response.content if block.type == 'text')
    if not text:
        raise StoryUnavailable('The storyteller returned no story. Please try again.')
    return json.loads(text)
