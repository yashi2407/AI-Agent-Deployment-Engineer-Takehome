"""Generate, judge, and revise bedtime stories.

With two more hours I would add a human-reviewed evaluation set for reading
levels, unsafe requests, and prompt injection, then measure judge agreement.
I would also add streamed progress updates and compare quality across providers.
"""
from backend.llm import (PROVIDERS, StoryUnavailable, call_model,
                         create_client, selected_provider)
from backend.prompts import JUDGE_PROMPT, STORY_PROMPT
from backend.schemas import Review, Story, StoryRequest

MAX_REVISIONS = 2


def generate_story(request: StoryRequest, client=None, provider=None):
    provider = provider or selected_provider()
    if client is None:
        with create_client(provider) as client:
            return generate_story(request, client, provider)
    bounds = (220, 400) if request.length == 'short' else (400, 650)
    context = {**request.model_dump(), 'word_range': bounds}
    history = []
    for revision in range(MAX_REVISIONS + 1):
        story = Story.model_validate(call_model(client, STORY_PROMPT, context, provider))
        review = Review.model_validate(call_model(client, JUDGE_PROMPT,
            {**request.model_dump(), **story.model_dump(), 'word_range': bounds}, provider))
        count = len(story.story.split())
        approved = (review.safe and min(review.scores.model_dump().values()) >= 4
                    and bounds[0] <= count <= bounds[1])
        history.append({**review.model_dump(), 'approved': approved,
                        'word_count': count, 'draft': revision + 1})
        if approved:
            return {**story.model_dump(), 'age': request.age, 'word_count': count,
                    'reading_minutes': max(1, round(count / 130)),
                    'revisions': revision, 'reviews': history, 'model': PROVIDERS[provider][0]}
        context = {**request.model_dump(), 'word_range': bounds,
                   'previous_draft': story.model_dump(), 'review': history[-1]}
    # Fail closed: never return a draft rejected by the final review.
    raise StoryUnavailable('This story needs more care. Try a simpler, gentler idea.')

