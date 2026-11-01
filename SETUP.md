# Running Moonbeam

Requires **Python 3.10+**, internet access, and a Gemini or Anthropic API key. Run commands from the project root. The Python server serves both frontend and backend; no Node.js, database, or frontend build is needed.

## Install

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell (no environment activation required):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure

Create `.env` beside `main.py`, or edit it if it already exists. For Gemini testing, get a key from [Google AI Studio](https://aistudio.google.com/apikey) and add:

```dotenv
STORY_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

Gemini was selected to reduce development costs through its available free tier; eligibility, quotas, and billing depend on your account. Each story or rewrite uses 2–6 model calls.

### Switch to Claude

Use an Anthropic key with access to the configured model, `claude-haiku-5-5`:

```dotenv
STORY_PROVIDER=claude
ANTHROPIC_API_KEY=your-anthropic-api-key
```

Claude is the default when `STORY_PROVIDER` is omitted and in `.env.example`. Both storyteller and judge use the selected provider, with no automatic fallback. Keep keys in `.env`, which is ignored by Git. Restart after configuration changes; exported environment variables take precedence over `.env`.

## Run

macOS/Linux, with the virtual environment activated:

```bash
python main.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe main.py
```

Open **http://127.0.0.1:8000** and keep the terminal running. Stop with **Ctrl+C**.

1. Enter an idea, choose an age and length, and click **Make a little magic**.
2. Read the story and expand the quality review to see scores. Generation may take a minute or two.
3. Use **Rewrite with my feedback** to request changes, or **Save story** to download it.

Rewrites pass through the same review process. A failed rewrite preserves the current story. Refreshing clears it, so download anything you want to keep. Review stories yourself before sharing them with a child.

## Test and inspect

Install and run the offline tests:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

On Windows, replace `python` with `.\.venv\Scripts\python.exe`. Tests mock model calls and require no API key. They verify application behavior, not live story quality.

- **Configuration:** http://127.0.0.1:8000/api/health — `configured: true` means a key is present; generating a story checks live access.
- **Interactive API:** http://127.0.0.1:8000/docs
- **CLI:** `python main.py --cli` (age 7, short story).
- **Development reload:** `python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000`

## Troubleshooting

| Problem | Action |
| --- | --- |
| Missing module | Install requirements with the same Python used to run the app. |
| Missing key or wrong provider | Check `.env`, matching key name, and exported variables; restart. |
| Story generation/checking fails | Check credentials, model access, quota, billing, and connectivity. Invalid model output can also cause this error. |
| “This story needs more care” | No draft passed within three attempts. Try a simpler idea or feedback request. |
| Port 8000 is occupied | Stop the other server, or run uvicorn with `--port 8001` and open that port. |
