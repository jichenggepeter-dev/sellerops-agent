# SellerOps Agent

SellerOps Agent is a governed AI operations workspace for customer support, refund review, risk triage, and product insights.

Milestone 1 is a dependency-free local MVP that proves the core product loop:

```text
CSV import
→ normalized cases
→ mock AI triage
→ Review Queue
→ human approval/rejection
→ Audit Log
```

Project docs:

- [PRD v0.1](PRD-v0.1.md)
- [MVP Build Plan](MVP-build-plan.md)
- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)

## Setup

Install the Python framework dependencies into the project virtual environment:

```bash
UV_CACHE_DIR=.uv-cache uv sync
```

Copy the example environment file if you want to override local defaults:

```bash
cp .env.example .env
```

By default the API uses local SQLite through `SELLEROPS_DB_PATH`. To use Postgres instead, set `SELLEROPS_DATABASE_URL`:

```text
SELLEROPS_DATABASE_URL=postgresql://sellerops:sellerops@localhost:5432/sellerops
```

## Run Locally With FastAPI

```bash
UV_CACHE_DIR=.uv-cache uv run uvicorn app.api.main:app --host 127.0.0.1 --port 8010
```

Then open:

```text
http://127.0.0.1:8010
```

API docs:

```text
http://127.0.0.1:8010/docs
```

## Run With Docker

Build and start the API service:

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8010
```

The container uses a named Docker volume for `/app/data`, so the local SQLite database persists across container restarts.

Optional connector/API settings can be passed through the shell environment before running Docker Compose:

```bash
SELLEROPS_TRIAGE_PROVIDER=openai \
SELLEROPS_OPENAI_API_KEY=... \
docker compose up --build
```

To start a local Postgres service for the production database migration path:

```bash
docker compose --profile postgres up postgres
```

Then run the API with:

```bash
SELLEROPS_DATABASE_URL=postgresql://sellerops:sellerops@localhost:5432/sellerops \
UV_CACHE_DIR=.uv-cache uv run uvicorn app.api.main:app --host 127.0.0.1 --port 8010
```

## Test

```bash
UV_CACHE_DIR=.uv-cache uv run pytest
```

GitHub Actions runs the same test suite on every push to `main` and every pull request.

Current coverage protects the core local product loop:

- health endpoint
- sample discovery
- policy defaults and versioned policy updates
- CSV import
- mock triage output
- Review Queue
- approval flow
- Audit Log
- review quality metrics
- eval example export
- empty CSV validation

## Database Migrations

Database schema is versioned with Alembic.

Run migrations:

```bash
UV_CACHE_DIR=.uv-cache uv run alembic upgrade head
```

Create a future migration:

```bash
UV_CACHE_DIR=.uv-cache uv run alembic revision -m "describe change"
```

The app calls migrations during startup through `init_db()`. The legacy `CREATE TABLE IF NOT EXISTS` path remains as a fallback if Alembic is unavailable.

## Fallback Local Prototype

```bash
python3 app/api/server.py
```

Then open:

```text
http://127.0.0.1:8000
```

If port 8000 is already in use:

```bash
SELLEROPS_PORT=8001 python3 app/api/server.py
```

## What Works Now

- Load sample CSV files from the sidebar.
- Import seller support or SaaS support cases.
- Normalize each row into a universal case model.
- Generate mock AI analysis:
  - category
  - severity
  - sentiment
  - risk score
  - risk labels
  - policy basis
  - suggested action
  - suggested owner
  - reply draft
  - human review flag
- View cases in Inbox.
- Review high-risk cases in Review Queue.
- Edit/review AI decisions.
- Approve or reject actions.
- Persist decisions and action records in Audit Log.
- View basic Insights:
  - top issue clusters
  - root cause hypotheses
  - weekly report draft
- Read and update policy settings:
  - refund policy
  - support policy
  - brand tone
  - routing rules
- Track review quality metrics.
- Export human-corrected eval examples.

## Backend Structure

The FastAPI backend is organized by responsibility:

```text
app/api/
  main.py                 # FastAPI app assembly, router registration, static files
  config.py               # project paths
  db.py                   # SQLite connection, schema initialization, row decoding
  logging_config.py       # JSON log formatting and request context
  middleware.py           # request ID propagation and request logging
  models.py               # SQLModel table definitions for the current schema
  repositories.py         # centralized SQL helpers for reads/writes
  schemas.py              # Pydantic request models
  time_utils.py           # shared time helper
  routers/
    core.py               # /api routes for cases, imports, reviews, audit, samples, policies, metrics, evals
  services/
    csv_import.py         # CSV parsing and header normalization
    triage.py             # mock AI triage service; future LLM provider seam
    cases.py              # case persistence, review decisions, audit logs
    connectors/           # approved external actions and dry-run behavior
    policies.py           # default policies, versioned policy updates, active context
    evals.py              # review quality metrics and eval export
  server.py               # dependency-free fallback local server
```

The frontend continues to call the same API paths, so the refactor does not change product behavior.

Persistence is intentionally in a transition state:

- Alembic owns schema versioning.
- SQLModel table classes document the schema and prepare for fuller ORM usage.
- Repository helpers centralize explicit SQL so services stay focused on workflow logic.
- Future work can move individual repositories from explicit SQL to SQLModel sessions without changing router contracts.

## Current Tech

The current implementation has a FastAPI service and a fallback dependency-free server:

- Backend: FastAPI, with a fallback Python `http.server`
- Database: SQLite
- Production database path: Postgres through `SELLEROPS_DATABASE_URL`
- Migrations: Alembic
- Schema models: SQLModel
- Frontend: static HTML/CSS/JS
- AI: mock triage rules
- Config: environment-driven settings via `.env`
- Tests: pytest + FastAPI TestClient
- Triage: provider interface with a deterministic mock provider
- Container: Dockerfile + docker-compose

The shape mirrors the planned production stack:

- Backend: FastAPI
- Database: Postgres
- Frontend: Next.js
- AI: structured LLM output with policy grounding

## Triage Provider

The AI layer is now behind a provider interface:

```text
app/api/services/triage.py           # TriageProvider protocol + MockTriageProvider
app/api/services/triage_registry.py  # provider selection from settings
```

Local default:

```text
SELLEROPS_TRIAGE_PROVIDER=mock
```

This keeps tests deterministic while leaving a clean path for a real provider:

```text
MockTriageProvider
OpenAITriageProvider
Future provider: Anthropic / local model / rules+LLM hybrid
```

Any provider must return the same structured triage contract used by the Review Queue and Audit Log.

To use OpenAI locally, set:

```text
SELLEROPS_TRIAGE_PROVIDER=openai
SELLEROPS_OPENAI_API_KEY=...
SELLEROPS_OPENAI_MODEL=gpt-4o-mini
```

The OpenAI provider uses the Responses API with Pydantic structured output parsing. If `SELLEROPS_TRIAGE_PROVIDER=openai` but no API key is configured, the app falls back to the mock provider by default:

```text
SELLEROPS_TRIAGE_FALLBACK_TO_MOCK=true
```

Set it to `false` if you want startup/triage to fail loudly when OpenAI credentials are missing.

## Slack Connector

Slack escalation is the first approved external action connector.

Configure:

```text
SELLEROPS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Behavior:

- Slack messages are only sent after a reviewer approves a `slack_escalation` action.
- If no webhook URL is configured, SellerOps records a dry-run `skipped` action in the Audit Log.
- The Audit Log stores the request payload and connector response.
- Rejected reviews never execute external actions.

## GitHub Connector

GitHub issue creation is available for approved `create_issue` actions.

Configure:

```text
SELLEROPS_GITHUB_TOKEN=...
SELLEROPS_GITHUB_REPO=owner/repo
```

Behavior:

- GitHub issues are only created after a reviewer approves a `create_issue` action.
- If token or repo is missing, SellerOps records a dry-run `skipped` action in the Audit Log.
- The connector uses GitHub REST API `POST /repos/{owner}/{repo}/issues`.
- `github_comment` is scaffolded for future issue comments, but requires an issue number/source mapping.
- Rejected reviews never execute external actions.

## Stripe Sandbox Refund Connector

Stripe sandbox refunds are available for approved `stripe_refund_sandbox` actions.

Configure:

```text
SELLEROPS_STRIPE_API_KEY=sk_test_...
SELLEROPS_STRIPE_ALLOW_LIVE_MODE=false
```

Behavior:

- Stripe refunds are only created after a reviewer approves a `stripe_refund_sandbox` action.
- If no Stripe key is configured, SellerOps records a dry-run `skipped` action in the Audit Log.
- Live keys starting with `sk_live` are blocked unless `SELLEROPS_STRIPE_ALLOW_LIVE_MODE=true`.
- The connector accepts connector-specific review payload fields such as `stripe_payment_intent`, `stripe_charge`, and `refund_amount`.
- The Audit Log stores the connector request metadata and Stripe response.
- Rejected reviews never execute external actions.

## Policy Settings

Default policies are created on startup for Seller Support and SaaS Support.

API:

```text
GET  /api/policies
GET  /api/policies?template_type=seller_support
POST /api/policies
```

Policy updates are versioned: when a new active policy is posted for the same workspace/template/type, the previous active policy is deactivated and the new one gets the next version.

Active policy context is passed into the triage provider so `policy_basis` can cite the relevant business rules.

## Eval and Review Quality

API:

```text
GET /api/metrics/review-quality
GET /api/evals/export
```

Review quality metrics compare the AI output against the human review decision:

```text
approval_rate
rejection_rate
edit_rate
category_correction_rate
severity_correction_rate
risk_score_correction_rate
action_correction_rate
owner_correction_rate
reply_correction_rate
eval_cases
```

Eval export returns examples with:

```text
case
ai_output
human_correction
```

These examples can later become JSONL eval sets for prompt and model regression testing.

## Next Milestone

Milestone 2 should add:

- Policy Settings UI.
- Real structured AI provider implementation with the existing mock fallback.
- Better risk taxonomy configuration.
- Stripe sandbox refund behind the Review Queue approval layer.
