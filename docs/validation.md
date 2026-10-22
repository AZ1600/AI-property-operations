# Validation and test boundaries

PropertyOps validates the application and infrastructure before its existing Azure
application deployment can run. This change provisions no Azure resources and
leaves the VNet migration as separate work. GitHub Actions usage remains subject
to the repository's Actions allowance and billing.

## Run locally

From an activated Python 3.11 virtual environment at the repository root:

```bash
python -m pip install -r requirements.txt
python -m pip install pytest pytest-subtests
python -m pytest -q

az bicep install --version v0.47.16
bash scripts/validate-infra.sh

git diff --check
```

No Azure login is required for template compilation. The script compiles every
`.bicep` file below `infra/`, exits on a compiler failure, and sends generated ARM
JSON to stdout redirected to `/dev/null` instead of creating generated repository
files. The same script runs in CI.

## Application coverage

Validated locally on 22 October 2026: **79 tests and 14 subtests passed**, using
Python 3.11 and pytest 9.1.1. Existing dependency deprecation warnings remain.

- Missing identity returns 401 on every currently protected API listed in the
  regression suite, without creating records or changing seeded decisions.
- Invalid Base64, JSON and principal/claim shapes return a generic 401 instead
  of crashing the identity parser or accepting a non-string actor.
- Unassigned, unknown and incorrectly cased application roles cannot access
  normal operations. Managers inherit normal user access.
- Users cannot approve or reject work, including when a request body claims a
  manager role or supplies a forged actor. Denied requests change no decisions
  and create no audit record.
- Manager approvals and rejections update both related statuses and record the
  actor from the authenticated principal, ignoring a forged body actor.
- Repeated or conflicting sequential decisions return 409 without extra audit
  records. Duplicate pending approval requests return 409.
- A database trigger deliberately rejects an audit insert. The request fails,
  neither status changes, and a retry succeeds after removing the trigger.
- Rules and stubbed AI suggestions create advice without deciding the associated
  approval. AI schema tests reject unsupported priority values, empty required
  fields, overlong content, and additional approval/dispatch fields.
- Provider responses that are incomplete or missing structured output fail
  explicitly. Provider and schema errors expose a safe message, not provider
  details or test credentials.

The old `tests/test_ai_triage.py` duplicated rules/workflow tests already present
in `tests/test_triage.py`. It now tests the AI adapter and schema directly; the
original rules and saved-suggestion workflow remain covered in `test_triage.py`.

## Test isolation

`tests/conftest.py` overrides inherited database and telemetry settings **before
collecting test modules**, because importing `app.main` creates tables. The
application's collection-time database is always in-memory SQLite. HTTP workflow
fixtures create their own independent in-memory databases.

Unmocked AI client construction raises an assertion. AI tests substitute local
provider stubs and never spend API credit. These controls apply to pytest runs;
they do not change application startup outside the test suite.

## Infrastructure and delivery

All **13 templates** compiled with Bicep CLI `v0.47.16` during local validation.
The CI job pins that version. Python tests and Bicep compilation run as separate
jobs. Deployment depends on both; it can run only for a non-PR event on `main`.
Only deployment receives `id-token: write` for the existing Azure OIDC login.
JUnit test results are uploaded even after a failing test step.

Compilation checks syntax, available resource types and module parameter wiring.
It is not an Azure What-If, authenticated deployment validation, quota check or
proof of private connectivity. Use Azure What-If and live verification before any
future infrastructure migration.

## Limits of this evidence

The auth tests send synthetic `X-MS-CLIENT-PRINCIPAL` headers through the real
FastAPI auth dependency. They test header parsing and application roles, not
Entra signatures, token expiry, issuer/audience validation, or deployed Easy Auth
settings. Azure Container Apps built-in authentication must remain correctly
configured as the trusted authentication layer; accepting this header directly
on an untrusted, separately exposed application server is not token validation.

Database tests use SQLite and sequential requests. They do not prove PostgreSQL
behavior, concurrent-decision safety, or multi-tenant data isolation. AI stubs
check adapter failures and state boundaries, not the quality or safety of real
model output. No new live Azure checks were run for this change.

References:

- [Bicep CLI compilation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-cli)
- [Container Apps authentication](https://learn.microsoft.com/en-us/azure/container-apps/authentication)
- [GitHub workflow jobs, dependencies and permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
