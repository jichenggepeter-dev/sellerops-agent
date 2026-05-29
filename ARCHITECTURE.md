# SellerOps Agent Architecture

SellerOps Agent is built as a governed operations layer for customer-facing teams. The system turns messy support, refund, and product feedback into structured cases, AI-assisted recommendations, human-reviewed actions, and audit/evaluation data.

Core principle:

```text
AI proposes. Humans approve. The system learns.
```

## Current System Shape

```text
CSV samples / future connectors
        |
        v
FastAPI routes
        |
        v
Service layer
        |
        v
Triage provider + policy context
        |
        v
SQLite persistence
        |
        v
Review queue / audit log / eval export
```

The current implementation is intentionally local-first, but the boundaries mirror a hosted production system:

- API layer: request/response contracts and route orchestration.
- Service layer: product workflow logic.
- Triage provider layer: mock or OpenAI-backed structured analysis.
- Policy layer: versioned business rules used by AI and review workflows.
- Connector layer: Slack, GitHub, Stripe sandbox, and future external actions.
- Persistence layer: database schema, migrations, and repository helpers.
- Web layer: static MVP interface that exercises the API.

## Backend Modules

```text
app/api/
  main.py                 FastAPI app setup, startup lifecycle, static frontend mount
  config.py               environment-driven settings
  db.py                   SQLite connection and Alembic migration startup
  models.py               SQLModel table definitions for the current schema
  repositories.py         centralized SQL read/write helpers
  schemas.py              Pydantic request models
  time_utils.py           shared UTC timestamp helper
  routers/
    core.py               public API routes for cases, import, reviews, policies, metrics, evals
  services/
    cases.py              case persistence, review decisions, audit records
    connectors.py         approved external actions and dry-run behavior
    csv_import.py         CSV parsing and flexible header normalization
    evals.py              review quality metrics and eval export
    openai_triage.py      OpenAI structured-output triage provider
    policies.py           default and versioned policies
    triage.py             provider protocol and deterministic mock provider
    triage_registry.py    provider selection and fallback behavior
```

## Request Flow

1. A user imports CSV data or, later, connector data.
2. The API normalizes raw rows into universal cases.
3. The active policy context is loaded.
4. A triage provider returns structured analysis.
5. The case and analysis are saved.
6. Risky or low-confidence items enter human review.
7. A reviewer approves, rejects, or edits the recommendation.
8. Approved actions can call external connectors.
9. Every decision and connector result is written to the audit log.
10. Human corrections can be exported as eval examples.

## Production Direction

The local MVP uses SQLite because it is simple and portable. The production direction is:

- PostgreSQL for hosted persistence.
- OAuth/API-key backed connectors for Shopify, Zendesk, GitHub, Slack, Stripe, and eventually marketplace APIs.
- Background jobs for imports, webhook processing, scheduled insight reports, and connector retries.
- Tenant/workspace isolation before any multi-user deployment.
- Stronger observability through structured logs, request IDs, action IDs, and connector trace records.
- Auth and role-based permissions before connecting live business systems.

## Safety Model

SellerOps Agent treats AI output as a recommendation, not an authority.

Risk controls:

- Structured AI output with schema validation.
- Policy-grounded reasoning.
- Human review for refunds, escalations, external writes, low confidence, and high risk.
- Dry-run behavior when connector credentials are missing.
- Stripe live-mode blocking by default.
- Audit log for every approval, rejection, and external action attempt.
- Eval export from human corrections.

## Why This Structure

This structure keeps the project useful while it grows:

- Routes stay thin and readable.
- Business workflows live in services.
- AI can be swapped from mock to OpenAI without changing the API.
- Connector failures do not corrupt core case state.
- Tests can protect the product loop without depending on real external systems.
- The frontend can evolve independently as long as the API contracts stay stable.
