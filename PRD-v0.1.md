# SellerOps Agent PRD v0.1

## 1. Product Summary

SellerOps Agent is a governed AI operations workspace for customer support, refund review, risk triage, and product insights.

It connects to existing commerce and support systems, turns messy customer signals into structured cases, recommends actions, routes high-risk work into human review, and records every approved action in an audit/evaluation loop.

Core principle:

```text
AI proposes. Humans approve. The system learns.
```

SellerOps does not become the merchant's storefront, ticketing system, or payment processor. It acts as the AI trust and operations layer on top of systems like Shopify, Stripe, Zendesk, GitHub, Slack, and CSV exports.

## 2. Target Users

### Template 1: Seller Support

For cross-border e-commerce teams using Shopify, Amazon, TikTok Shop, Stripe, Zendesk, Gmail, or exported CSV workflows.

Primary problems:
- Refund requests are scattered across tickets, emails, order notes, and comments.
- Small teams cannot consistently identify customer churn risk, logistics issues, policy risk, or repeated product complaints.
- AI auto-replies and auto-refunds are risky without human approval, policy grounding, and audit logs.
- Chinese-speaking operators often need to process English-language customer feedback and produce internal bilingual summaries.

Primary value:
- Faster support triage.
- Safer refund review.
- High-risk case escalation.
- Weekly product and operations insight reports.

### Template 2: SaaS Support

For AI SaaS, developer tools, and open-source product teams using GitHub Issues, Zendesk, Slack, Linear, Discord exports, or CSV support data.

Primary problems:
- Feedback is split across GitHub issues, customer tickets, community posts, and public complaints.
- Product teams need to separate bugs, feature requests, documentation gaps, onboarding friction, and churn risks.
- Maintainers and PMs need weekly insight reports, not just a pile of raw issues.

Primary value:
- Issue triage.
- Product insight clustering.
- Escalation to engineering/support.
- Audit/eval loop for AI classification quality.

## 3. Product Positioning

SellerOps Agent turns support, order, and product feedback into governed actions.

One-line pitch:

```text
An AI operations analyst for customer-facing teams: classify, prioritize, draft, route, review, and learn from every customer signal.
```

What makes it different from a normal support chatbot:
- It starts with read-only intelligence and human review, not unsafe automation.
- It supports refund and action workflows, but every risky action requires approval.
- It includes policy basis, confidence, risk labels, and audit logs.
- Human corrections become evaluation data.
- It serves both merchant support and product insight workflows.

## 4. Core Workflow

```text
Customer feedback / support tickets / GitHub issues / order refund requests
→ AI classification
→ risk scoring
→ reply/action recommendation
→ human review queue
→ approved actions to Slack/GitHub/Zendesk/Stripe sandbox
→ audit log
→ corrections feed back into evals and policies
```

## 5. MVP Scope

### Must Have

Data ingestion:
- CSV upload for support tickets, orders/refund requests, comments/reviews.
- Flexible CSV field mapping for unknown schemas.
- GitHub public repo issues via repo URL.
- Stripe sandbox test payment/refund flow.

Case processing:
- AI classification.
- Severity and sentiment detection.
- Risk scoring.
- Risk label assignment.
- Suggested owner/team.
- Suggested action.
- Reply draft when relevant.
- Human review requirement flag.
- Policy basis/reason for AI judgment.

Human review:
- Review Queue for reply drafts, refund recommendations, escalations, GitHub actions, and owner assignments.
- Users can edit labels, risk level, reply draft, suggested action, owner, and correction notes.
- Users can approve/reject actions.
- Every approval/rejection is logged.

Insights:
- Top issue clusters.
- Top affected customers/orders.
- Root cause hypotheses.
- Weekly report export.

Settings:
- Business template selection: Seller Support or SaaS Support.
- Refund policy / support policy text.
- Brand tone.
- Routing rules.
- Risk thresholds.

Audit/evals:
- Record original AI outputs and human-corrected outputs.
- Track approval rate.
- Track classification correction rate.
- Track refund decision agreement in sandbox workflows.

### Should Have

- Slack escalation via webhook.
- GitHub issue/comment creation after approval.
- Basic PII detection and masking.
- Weekly report as Markdown export.
- Sample datasets for both templates.

### Not MVP

- Direct customer-facing auto-replies.
- Live Stripe refunds.
- Live Shopify refunds.
- TikTok Shop connector.
- Amazon connector.
- Multi-tenant billing.
- Full Zendesk customer reply automation.

## 6. Real Integration Strategy

Users do not connect to a local port. In production, they use hosted HTTPS endpoints and OAuth/API connectors.

Development ports:

```text
Frontend: http://localhost:3000
Backend: http://localhost:8000
Postgres: localhost:5432
```

Production endpoints:

```text
https://sellerops.ai
https://api.sellerops.ai
POST /webhooks/shopify/orders
POST /webhooks/shopify/refunds
POST /webhooks/zendesk/tickets
POST /webhooks/stripe/events
```

### Phase 1 Connectors

CSV:
- Upload support tickets, order/refund requests, and comments.
- User confirms field mapping before import.

GitHub:
- Enter public repo URL.
- Pull open issues.
- Optional approved action: create GitHub issue/comment.

Stripe Sandbox:
- Create test customer/payment.
- Generate refund recommendation.
- Human approval required.
- Execute test refund.
- Write audit log.

Slack:
- Send approved escalation or high-risk alert to a configured Slack webhook.

### Phase 2 Connectors

Zendesk:
- Read tickets.
- Write internal notes.
- Do not directly reply to customers in early versions.

Shopify:
- Read orders, customers, fulfillment status, and refund state.
- Listen to webhooks for order/refund events.
- Recommend refund action, but human approval required.

### Phase 3 Connectors

Shopify real action layer:
- Prepare refund operation.
- Require human approval.
- Record audit log.

TikTok Shop / Amazon:
- Explore API access and platform review requirements.
- Do not depend on these for MVP.

## 7. Case Data Model

Use a universal case model with source-specific metadata.

```text
Case
- id
- workspace_id
- template_type: seller_support | saas_support
- source_type: csv | github | stripe | zendesk | shopify | slack | manual
- source_id
- title
- message
- customer_name
- customer_email
- order_id
- amount
- currency
- product_name
- status
- created_at
- imported_at
- metadata_json
```

AI analysis fields:

```text
CaseAnalysis
- id
- case_id
- category
- severity: low | medium | high | critical
- sentiment: positive | neutral | negative | angry | urgent
- risk_score: 0-100
- risk_labels: string[]
- policy_basis
- reason
- suggested_action
- suggested_owner
- reply_draft
- confidence_score: 0-1
- requires_human_review: boolean
- model_name
- prompt_version
- created_at
```

Review fields:

```text
ReviewDecision
- id
- case_id
- analysis_id
- reviewer_id
- decision: approve | reject | edit | escalate
- corrected_category
- corrected_severity
- corrected_risk_score
- corrected_risk_labels
- corrected_action
- corrected_owner
- corrected_reply
- correction_reason
- add_to_eval_dataset: boolean
- created_at
```

Action/audit fields:

```text
ActionLog
- id
- case_id
- decision_id
- action_type: slack_escalation | github_comment | github_issue | stripe_refund_sandbox | assign_owner | export_report
- status: pending | executed | failed | skipped
- request_payload_json
- response_payload_json
- executed_by
- executed_at
```

Policy fields:

```text
Policy
- id
- workspace_id
- template_type
- name
- policy_type: refund | support | brand_tone | routing | risk_threshold
- body
- version
- active
- created_at
```

## 8. AI Output Contract

Every AI analysis should produce structured JSON.

Required fields:

```json
{
  "category": "refund_request",
  "severity": "high",
  "sentiment": "angry",
  "risk_score": 87,
  "risk_labels": ["churn_risk", "refund_policy_sensitive", "public_complaint_risk"],
  "policy_basis": "Refund policy allows refunds within 30 days if the item is undelivered or damaged.",
  "reason": "Customer reports delayed delivery, threatens public complaint, and order is within refund window.",
  "suggested_action": "refund_review",
  "suggested_owner": "support_lead",
  "reply_draft": "Hi {{customer_name}}, sorry for the delay...",
  "confidence_score": 0.82,
  "requires_human_review": true
}
```

## 9. Risk Taxonomy

Initial risk labels:

- churn_risk
- angry_customer
- high_value_customer
- repeat_complaint
- refund_policy_sensitive
- logistics_delay
- product_quality_issue
- public_complaint_risk
- legal_or_compliance_risk
- pii_detected
- low_confidence
- ai_misreply_risk
- ai_overpromise_risk
- needs_human_escalation

## 10. Page Structure

### Onboarding

Step 1: Select template
- Seller Support
- SaaS Support

Step 2: Connect source
- CSV
- GitHub public repo
- Stripe sandbox
- Slack webhook

Step 3: Define goal
- Reduce support load
- Detect risk
- Review refunds
- Generate insights

### Inbox

Main triage surface:
- Left: case list with filters.
- Center: selected case details.
- Right: AI analysis, risk reasoning, suggested action, and review controls.

Filters:
- Source
- Category
- Severity
- Risk label
- Requires review
- Owner
- Status

### Review Queue

For all actions requiring approval:
- Reply drafts.
- Refund recommendations.
- Slack escalations.
- GitHub actions.
- Owner assignments.

Reviewer can:
- Edit labels.
- Edit risk score.
- Edit reply draft.
- Change action.
- Assign owner.
- Approve/reject.
- Add correction reason.
- Mark as eval case.

### Insights

Initial modules:
- Top issue clusters.
- Top affected customers/orders.
- Root cause hypotheses.
- Weekly report export.

Later modules:
- Risk trend over time.
- Suggested product/ops fixes.
- Segment comparison.

### Settings

- Template.
- Policies.
- Brand tone.
- Routing rules.
- Risk thresholds.
- Integrations.

### Audit & Evals

MVP can start as an audit/corrections panel instead of a full separate page.

Metrics:
- AI action approval rate.
- Classification correction rate.
- Refund decision agreement.
- Number of high-risk cases caught.
- Number of cases marked as eval examples.

## 11. Safety Principles

Non-negotiable:

```text
AI never sends customer-facing messages without approval.
AI never executes refunds without approval.
High-risk or low-confidence cases always require review.
PII should be detected and masked where possible.
Every action must have an audit log.
Every AI decision must include a reason or policy basis.
Human corrections become evaluation data.
```

## 12. Technical Architecture

Chosen stack:

```text
Frontend: Next.js
Backend: FastAPI
Database: Postgres
Jobs: background worker / queue
AI workflow: deterministic pipeline + agentic reasoning steps
Integrations: GitHub API, Stripe sandbox, Slack webhook, later Zendesk/Shopify
```

Suggested repository structure:

```text
sellerops-agent/
  apps/
    web/                 # Next.js
    api/                 # FastAPI
  packages/
    shared-schema/       # shared JSON schemas/types
  docs/
    PRD.md
    architecture.md
    eval-plan.md
  samples/
    seller-support/
    saas-support/
```

Pipeline:

```text
Import source
→ Normalize to Case
→ Apply policy context
→ Run AI analysis
→ Save CaseAnalysis
→ If high-risk/actionable, create Review Queue item
→ User reviews
→ Approved action executes via connector
→ ActionLog saved
→ Corrections update eval metrics
```

## 13. Four-Week Build Plan

### Week 1: Foundations

Goal: Local system with CSV import and case normalization.

Deliverables:
- Repo scaffold.
- FastAPI app.
- Postgres schema.
- Next.js shell.
- CSV upload and field mapping.
- Universal Case model.
- Sample Seller Support and SaaS Support datasets.

### Week 2: AI Triage and Review Queue

Goal: AI analysis loop with human review.

Deliverables:
- Structured AI output contract.
- Policy settings.
- Case analysis pipeline.
- Inbox view.
- Review Queue.
- Human correction capture.
- Audit log table.

### Week 3: Integrations and Actions

Goal: Prove governed action execution.

Deliverables:
- GitHub public repo issue import.
- Approved GitHub issue/comment action.
- Slack webhook escalation.
- Stripe sandbox test refund.
- ActionLog UI.
- Basic approval metrics.

### Week 4: Insights and Portfolio-Ready Product

Goal: Product-grade story and usable MVP.

Deliverables:
- Insights page.
- Top issue clusters.
- Root cause hypotheses.
- Weekly report export.
- Correction/approval metrics.
- Seed demo data.
- README.
- Case study draft.
- Deployment plan.

## 14. Portfolio and Resume Narrative

Potential resume bullet:

```text
Building SellerOps Agent, a governed AI operations workspace for customer support, refund review, and product insights, combining AI triage, human-in-the-loop approvals, audit logs, and integrations with GitHub, Slack, Stripe sandbox, and future Shopify/Zendesk connectors.
```

More TikTok-aligned version:

```text
Designed a trust-oriented AI agent workflow for seller/customer operations, classifying support signals, detecting refund and policy risks, generating approved reply drafts, and tracking human review corrections as evaluation data.
```

## 15. Open Questions

- Should Seller Support and SaaS Support share one UI with template-specific language, or eventually become two separate product surfaces?
- Which real beta user should be targeted first: cross-border seller, AI SaaS team, or open-source maintainer?
- Should Zendesk be Phase 2 or pulled into Phase 1 if a real user has access?
- Which LLM provider should be used first for cost and structured output reliability?
- How much PII masking is required before testing with real merchant data?

