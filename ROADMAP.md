# SellerOps Agent Roadmap

This roadmap keeps the project focused on becoming a real product, not a one-off interview demo.

## Phase 1: Backend Production Baseline

Goal: make the local backend reliable, testable, and clear enough for public review.

Status: complete.

Completed:

- FastAPI backend.
- SQLite persistence.
- Alembic migrations.
- SQLModel schema definitions.
- CSV import for seller support and SaaS support samples.
- Deterministic mock AI triage provider.
- OpenAI triage provider behind a provider interface.
- Versioned policies.
- Review Queue.
- Audit Log.
- Review quality metrics.
- Eval export.
- Slack, GitHub, and Stripe sandbox connector paths.
- Dockerfile and Docker Compose.
- GitHub Actions CI.
- Request ID propagation and JSON request logs.
- Connector modules split by provider.
- Local Postgres Docker profile for the upcoming database adapter.
- Configurable SQLite/Postgres database adapter.
- Workspace ID scaffold on imported cases.
- AI/provider failure states with forced human review.
- Fallback triage path when configured provider fails.

## Phase 2: Product Loop Hardening

Goal: make one complete workflow feel real from import to review to action.

Status: next.

Build:

- Better case filters and queue states.
- More explicit action types:
  - reply draft
  - Slack escalation
  - GitHub issue/comment
  - Stripe sandbox refund
  - owner assignment
- Action preview before approval.
- Reviewer edit history.
- Better eval examples from human corrections.
- Markdown weekly insight report export.

Started:

- Action preview before approval.
- Case status flow for `needs_review`, `analyzed`, `approved`, `action_executed`, `action_failed`, and `rejected`.
- Reviewer edit history for field-level AI-to-human corrections.
- Action result details in audit logs, including preview payload, external URL, failure reason, and retryability.

Success criteria:

- A seller-support sample can produce refund recommendations, reply drafts, escalations, and audit records.
- A SaaS-support sample can produce issue clusters, owner routing, GitHub actions, and a weekly insight report.
- No risky external action runs without approval.

## Phase 3: Frontend Workspace

Goal: replace the static MVP screen with a sharper operations console.

Build:

- Inbox view.
- Review Queue view.
- Case detail page.
- Audit Log view.
- Insights/report page.
- Settings and policy editor.
- Connector configuration screens.

Design direction:

- Seller template: modern merchant operations workspace.
- SaaS template: dense, technical, product-ops workspace.
- Keep the first screen useful, not a marketing landing page.

## Phase 4: Real Connector Path

Goal: prove that teams can connect SellerOps Agent to real systems safely.

Build:

- GitHub issue import from public repo URL.
- Slack webhook configuration.
- Stripe sandbox setup guide and test refund flow.
- Webhook endpoint structure for future Shopify/Zendesk integrations.
- Connector audit traces and retry-safe action records.

Not yet:

- Live Stripe refunds.
- Live Shopify refunds.
- Direct customer-facing auto-replies.
- TikTok Shop or Amazon marketplace connectors.

## Phase 5: AI Governance and Evaluation

Goal: make the AI layer measurable, controllable, and credible.

Build:

- Prompt/version tracking.
- Golden eval dataset generated from reviewed cases.
- Regression test runner for triage output quality.
- Risk-label precision checks.
- Policy compliance checks.
- PII detection and masking.
- Approval/correction dashboards.

## Phase 6: Hosted MVP Readiness

Goal: prepare for a real pilot deployment.

Build:

- PostgreSQL.
- Auth.
- Workspace and user model.
- Role-based permissions.
- Background job queue.
- Deployment config.
- Secrets management.
- Basic monitoring.

Hosted MVP should support read-heavy workflows first. Write actions should remain sandboxed or human-approved until trust, permissions, and connector policies are mature.
