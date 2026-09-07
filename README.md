# PropertyOps AI Agent

A FastAPI backend for managing properties, maintenance requests, and human approval decisions. AI triage is planned; it is not implemented yet.

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

## Next milestone

Add maintenance triage suggestions (priority, trade, and recommended next step) for human review, while retaining the approval workflow.
