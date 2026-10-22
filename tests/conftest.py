"""Keep collection and tests independent of developer databases and AI accounts."""

import os

# app.main creates tables during import, before pytest fixtures can run.
# Override inherited production settings before collecting any test modules.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = ""
os.environ["TRIAGE_MODE"] = "rules"
os.environ["OPENAI_API_KEY"] = ""

import pytest


@pytest.fixture(autouse=True)
def block_unmocked_ai(monkeypatch):
    from app import ai_triage

    def unexpected_client(*args, **kwargs):
        raise AssertionError("Tests must mock AI clients; external AI calls are disabled")

    monkeypatch.setattr(ai_triage, "OpenAI", unexpected_client)
