"""Start the Moonbeam web app or generate a story from the terminal."""
import argparse
import json

from anthropic import APIError
from google.genai.errors import APIError as GeminiAPIError
from httpx import TransportError
from pydantic import ValidationError

from backend.app import app
from backend.schemas import StoryRequest
from backend.storyteller import StoryUnavailable, generate_story


def main():
    parser = argparse.ArgumentParser(description='Moonbeam bedtime storyteller')
    parser.add_argument('--cli', action='store_true')
    args = parser.parse_args()
    if args.cli:
        try:
            result = generate_story(StoryRequest(prompt=input('What story would you like? ')))
            print(result['title'] + '\n\n' + result['story'])
        except (StoryUnavailable, APIError, GeminiAPIError, TransportError, ValidationError, json.JSONDecodeError) as exc:
            parser.exit(1, f'Generation failed ({type(exc).__name__}). Check your key and request.\n')
    else:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=8000)


if __name__ == '__main__':
    main()
