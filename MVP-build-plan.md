# SellerOps Agent MVP Build Plan

## Build Objective

Build a local, usable MVP that proves the core loop:

```text
Import cases
→ AI triage
→ risk/action recommendation
→ human review
→ approved action
→ audit/eval signal
```

The MVP should feel like a real operations workspace, not a toy demo. The first version can run locally, but its architecture should leave a clean path to hosted deployment and real connectors.

## Phase 0: Project Setup

Decisions:
- Monorepo.
- `apps/web`: Next.js.
- `apps/api`: FastAPI.
- `Postgres`: primary database.
- `SQLAlchemy` or `SQLModel` for backend models.
- `pydantic` schemas for AI output contracts.

Initial directories:

```text
SellerOps-Agent/
  PRD-v0.1.md
  MVP-build-plan.md
  app/
    web/
    api/
  samples/
    seller-support/
    saas-support/
  docs/
```

## Phase 1: Data and Case Model

### Backend Models

Create:
- `Workspace`
- `Policy`
- `Case`
- `CaseAnalysis`
- `ReviewDecision`
- `ActionLog`
- `Integration`

### CSV Import

Support:
- Support ticket CSV.
- Order/refund request CSV.
- Free-form CSV with field mapping.

First mapping fields:
- `title`
- `message`
- `customer_name`
- `customer_email`
- `order_id`
- `amount`
- `product_name`
- `status`
- `created_at`
- `metadata`

### Sample Data

Create sample datasets:
- `seller-support/refund_requests.csv`
- `seller-support/customer_messages.csv`
- `saas-support/github_issues.csv`
- `saas-support/support_tickets.csv`

## Phase 2: AI Triage Pipeline

### Deterministic Pipeline

1. Normalize input into `Case`.
2. Load active policy and brand tone.
3. Build AI prompt with structured output contract.
4. Validate JSON response.
5. Save `CaseAnalysis`.
6. Create review item if:
   - `requires_human_review = true`
   - `risk_score >= threshold`
   - `confidence_score < threshold`
   - suggested action is refund, escalation, customer-facing reply, or external write action.

### AI Output

Required:
- `category`
- `severity`
- `sentiment`
- `risk_score`
- `risk_labels`
- `policy_basis`
- `reason`
- `suggested_action`
- `suggested_owner`
- `reply_draft`
- `confidence_score`
- `requires_human_review`

### Fallback

If LLM call fails:
- Save case as `analysis_failed`.
- Add to Review Queue.
- Do not generate actions.

## Phase 3: Web UI

### Onboarding

Initial screens:
- Choose template: Seller Support / SaaS Support.
- Choose source: CSV / GitHub / Stripe sandbox / Slack.
- Define goal: reduce support load / detect risk / review refunds / generate insights.

### Inbox

Three-column layout:
- Left: case list and filters.
- Center: raw case content.
- Right: AI analysis and suggested action.

Filters:
- source
- category
- severity
- risk label
- review required
- owner
- action type

### Review Queue

Fields editable by reviewer:
- category
- severity
- risk score
- risk labels
- suggested action
- owner
- reply draft
- correction reason
- add to eval dataset

Actions:
- approve
- reject
- edit and approve
- escalate

### Insights

MVP cards:
- Top issue clusters.
- Top affected customers/orders.
- Root cause hypotheses.
- Weekly report export.

### Settings

MVP settings:
- refund policy
- support policy
- brand tone
- routing rules
- risk threshold
- confidence threshold
- Slack webhook URL

## Phase 4: Integrations

### GitHub Public Issues

MVP:
- Input repo URL.
- Pull open issues.
- Normalize issues into cases.

Approved actions:
- Create comment on existing issue.
- Create new issue from insight or escalation.

### Slack Webhook

MVP:
- Configure incoming webhook.
- Send approved escalation message.

Message format:
- Case title.
- Risk labels.
- Suggested owner.
- AI reason.
- Link to case in SellerOps.

### Stripe Sandbox

MVP:
- Create test payment.
- Attach order/customer metadata.
- Generate refund recommendation.
- Human approval required.
- Execute test refund.
- Log result.

Do not support live refunds in MVP.

## Phase 5: Metrics and Eval Loop

MVP metrics:
- AI approval rate.
- Classification correction rate.
- Average risk score by category.
- Refund decision agreement.
- Number of high-risk cases.
- Number of cases marked for eval.

Eval dataset:
- Store human-corrected examples.
- Export JSONL later for batch evals.

## Phase 6: Deployment Path

Local:
- Docker Compose for Postgres, API, web.

Hosted path:
- Frontend: Vercel.
- Backend: Render/Fly.io/Railway.
- DB: Supabase/Neon/Postgres.
- Secrets: provider secret store.

Production integration endpoints:

```text
POST /webhooks/shopify/orders
POST /webhooks/shopify/refunds
POST /webhooks/zendesk/tickets
POST /webhooks/stripe/events
```

These are not required for local MVP, but route names should be reserved early.

## First Engineering Milestone

Milestone 1 is complete when:
- User can upload a seller-support CSV.
- Cases appear in Inbox.
- AI analysis is generated and saved.
- High-risk cases appear in Review Queue.
- Reviewer can edit and approve/reject.
- Audit log records the decision.

This is the smallest meaningful product loop.

