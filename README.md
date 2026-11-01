# Moonbeam · Little stories. Sweet dreams.

Moonbeam creates bedtime stories for children ages **5–10**. A separate LLM judge reviews each draft and guides up to two revisions before the story is displayed. Users can submit feedback to request a new version, which goes through the same review process.

I selected **Gemini 2.5 Flash-Lite for development and testing** to use its available free tier while iterating on a workflow that makes multiple model calls. **Claude Haiku 5.5 remains supported**: change the provider and key in `.env` to use it, without changing application code. Free-tier usage is subject to Google's eligibility, quotas, and billing tier; see [Google's pricing](https://ai.google.dev/gemini-api/docs/pricing).

## Documentation

- **[SETUP.md](SETUP.md)** — step-by-step installation, API-key setup, running the app, switching providers, testing, and troubleshooting.
- **[SUBMISSION.md](SUBMISSION.md)** — assignment explanation, system block diagram, prompting/judge design, feedback flow, provider comparison, limitations, and next steps.

## Quick start · macOS/Linux

Requires Python 3.10+ and a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Run from the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `.env` in the project root, or edit it if it already exists:

```dotenv
STORY_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

Start the app:

```bash
python main.py
```

Open **http://127.0.0.1:8000**. The Python server serves both the frontend and backend; no Node.js installation or separate frontend server is needed. Stop it with **Ctrl+C**.

To use Claude instead, follow [Switch to Claude](SETUP.md#switch-to-claude). The checked-in `.env.example` and the application's fallback default use Claude; explicitly select Gemini as shown above for testing. No credentials are included in the submission.

## Project structure

```text
backend/
  app.py          # HTTP routes, environment loading, frontend serving
  storyteller.py  # Story generation, judging, and bounded revisions
  llm.py          # Provider selection and separate Claude/Gemini SDK calls
  prompts.py      # Storyteller and judge system prompts
  schemas.py      # Request and output validation
frontend/
  index.html      # Story request, reading view, and feedback form
  style.css       # Responsive bedtime theme
  app.js          # Loading/error states, story rewrites, and downloads
tests/
  test_app.py     # Offline workflow, API, and SDK-adapter tests
main.py           # Web/CLI entry point
.env.example      # Provider/key template without credentials
requirements.txt
requirements-dev.txt
SETUP.md
SUBMISSION.md
```

The frontend uses system fonts and CSS illustrations. Stories are rendered as text. Prompts, stories, and feedback are not persisted on the server; the current story stays in browser memory until the page is refreshed. Requests are sent to the selected model provider. Keys stay on the server, and `.env` is excluded from Git.
