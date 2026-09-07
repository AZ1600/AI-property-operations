# PropertyOps AI Agent

A FastAPI backend for managing properties, maintenance requests, and human approval decisions. Initial triage suggestions use keyword rules; an AI model is not connected yet.

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

Suggestions include priority, trade, recommended action, rationale, and source (`rules-v1`). They do not change the request's priority or status, create an approval, or dispatch work. Keyword rules cannot understand negation or reliably assess safety; all suggestions require human review.

Restart the app after updating to create the new suggestions table. Existing tables do not require changes.

Run tests using `python -m unittest discover -s tests -v` in your virtual environment.

The next milestone is connecting an AI model for richer suggestions while retaining human review.
