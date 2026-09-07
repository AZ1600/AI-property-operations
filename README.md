# PropertyOps AI Agent

A FastAPI backend for managing properties, maintenance requests, and human approval decisions. Triage uses local keyword rules by default, so development needs no API credit. OpenAI suggestions are available through an explicit configuration switch.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API. The app creates a local `propertyops.db` SQLite database in the directory where it is started. Existing data is not included in this repository.

## Current workflow

1. Create a property with `POST /properties`.
2. Submit an issue with `POST /maintenance` using the property ID.
3. Request review with `POST /approvals` using the maintenance request ID.
4. Use `POST /approvals/{approval_id}/approve` or `POST /approvals/{approval_id}/reject`.
5. Inspect `GET /maintenance` and `GET /audit-logs`.

Both decisions update the linked maintenance request and create an audit event in the same database transaction. Duplicate pending approvals and repeated decisions return HTTP 409.

The API is currently a local development prototype without authentication. The audit actor is currently the fixed value `human`.

## Maintenance triage

Call `POST /maintenance/{maintenance_id}/triage` to save a suggestion, then `GET /maintenance/{maintenance_id}/triage` to view its history. Each POST saves a new suggestion. Unknown maintenance IDs return 404.

Suggestions include priority, trade, recommended action, rationale, and source (`rules-v1` or `openai:<model>`). They do not change the request's priority or status, create an approval, or dispatch work. Keyword rules cannot understand negation or reliably assess safety; all suggestions require human review.

Restart the app after updating to create the new suggestions table. Existing tables do not require changes.

Run tests using `python -m unittest discover -s tests -v` in your virtual environment.

## Work without API credit

Install the updated requirements. Triage defaults to `rules`, even when an API key is saved. To make that choice explicit, add this line to the root `.env` file:

```dotenv
TRIAGE_MODE=rules
```

You can keep the saved key in place. Rules mode makes no model requests. Open `GET /triage-config` to check the selected mode; this endpoint reveals no credentials and does not contact OpenAI. Its `configured` flag checks local settings only, not provider credit or access.

## Enable AI later

If starting fresh, copy `.env.example` to a **file** named `.env` in the project root (alongside `requirements.txt`, outside `.venv`). Do not overwrite an existing key file. When API credit is available, set `TRIAGE_MODE=openai`, `OPENAI_API_KEY` and optionally `OPENAI_MODEL` (default `gpt-5-mini`). Existing environment variables override the file. Keep `.env` private; it is ignored by Git.

Restart the server and call the existing triage endpoint. OpenAI mode sends only the issue text with instructions to the Responses API using structured output and `store=False`. Saved suggestions identify their source as `openai:<model>`. Missing keys, invalid modes, AI errors or refusals return HTTP 503 without saving a suggestion; they do not silently fall back to rules. Check key permissions, API billing and model access if a request fails.

Both modes only suggest actions. Human approval, maintenance status and audit decisions remain separate. This is a development prototype, not an emergency response service.
