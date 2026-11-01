"""HTTP endpoints and frontend serving."""
import json
import os
from pathlib import Path

from anthropic import APIError
from google.genai.errors import APIError as GeminiAPIError
from httpx import TransportError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from backend.llm import PROVIDERS, selected_provider
from backend.schemas import StoryRequest
from backend.storyteller import StoryUnavailable, generate_story

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
FRONTEND = ROOT / 'frontend'
app = FastAPI(title='Moonbeam')
app.mount('/static', StaticFiles(directory=FRONTEND), name='static')


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(FRONTEND / 'index.html')


@app.get('/api/health')
def health():
    try:
        provider = selected_provider()
    except StoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    model, key_name = PROVIDERS[provider]
    return {'status': 'ok', 'provider': provider, 'model': model,
            'configured': bool(os.getenv(key_name))}


@app.post('/api/stories')
def create_story(request: StoryRequest):
    try:
        return generate_story(request)
    except StoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except (APIError, GeminiAPIError, TransportError, ValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(502, 'We could not finish checking this story. Please try again.') from exc
