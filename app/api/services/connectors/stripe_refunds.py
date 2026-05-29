"""Stripe sandbox refund actions."""

from __future__ import annotations

from app.api.config import get_settings


def create_stripe_sandbox_refund(payload: dict, case: dict | None = None) -> dict:
    settings = get_settings()
    case = case or {}
    payment_reference = (
        payload.get("stripe_payment_intent")
        or payload.get("stripe_charge")
        or case.get("source_id")
        or case.get("order_id")
    )
    amount = payload.get("refund_amount") or case.get("amount")
    request_payload = {
        "payment_reference": payment_reference,
        "amount": amount,
        "reason": payload.get("correction_reason") or "Approved SellerOps refund review.",
        "case_id": payload.get("case_id"),
    }
    if not settings.stripe_api_key:
        return {
            "status": "skipped",
            "response": {
                "message": "Stripe API key is not configured.",
                "dry_run": True,
                "payload": request_payload,
            },
        }
    if settings.stripe_api_key.startswith("sk_live") and not settings.stripe_allow_live_mode:
        return {
            "status": "skipped",
            "response": {
                "message": "Live Stripe keys are blocked unless SELLEROPS_STRIPE_ALLOW_LIVE_MODE=true.",
                "dry_run": True,
                "payload": request_payload,
            },
        }
    if not payment_reference:
        return {
            "status": "skipped",
            "response": {
                "message": "No Stripe payment reference was provided.",
                "dry_run": True,
                "payload": request_payload,
            },
        }

    try:
        import stripe
    except ImportError:
        return {
            "status": "failed",
            "response": {"message": "stripe package is not installed."},
        }

    stripe.api_key = settings.stripe_api_key
    refund_args = {
        "metadata": {
            "sellerops_case_id": str(payload.get("case_id")),
            "sellerops_decision": payload.get("decision", ""),
        }
    }
    if str(payment_reference).startswith("pi_"):
        refund_args["payment_intent"] = payment_reference
    else:
        refund_args["charge"] = payment_reference
    if amount is not None:
        try:
            refund_args["amount"] = int(round(float(amount) * 100))
        except (TypeError, ValueError):
            pass
    try:
        refund = stripe.Refund.create(**refund_args)
        return {
            "status": "executed",
            "response": {
                "id": refund.get("id") if hasattr(refund, "get") else getattr(refund, "id", None),
                "status": refund.get("status") if hasattr(refund, "get") else getattr(refund, "status", None),
                "object": dict(refund) if isinstance(refund, dict) else str(refund),
            },
        }
    except Exception as exc:
        return {
            "status": "failed",
            "response": {
                "message": str(exc),
                "payload": request_payload,
            },
        }
