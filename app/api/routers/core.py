"""Core API routes for health, samples, cases, reviews, and audit."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.config import ROOT
from app.api.schemas import CsvImportRequest, PolicyUpsertRequest, ReviewRequest
from app.api.services.cases import (
    audit_logs,
    create_review,
    insert_case_and_analysis,
    latest_cases,
)
from app.api.services.csv_import import parse_csv_text
from app.api.services.evals import export_eval_examples, review_quality_metrics
from app.api.services.policies import list_policies, upsert_policy
from app.api.time_utils import utc_now


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "fastapi", "time": utc_now()}


@router.get("/cases")
def get_cases() -> dict[str, Any]:
    return {"cases": latest_cases(False)}


@router.get("/review-queue")
def get_review_queue() -> dict[str, Any]:
    return {"cases": latest_cases(True)}


@router.get("/audit")
def get_audit() -> dict[str, Any]:
    return {"logs": audit_logs()}


@router.get("/metrics/review-quality")
def get_review_quality_metrics() -> dict[str, Any]:
    return review_quality_metrics()


@router.get("/evals/export")
def get_eval_export() -> dict[str, Any]:
    return {"examples": export_eval_examples()}


@router.get("/samples")
def get_samples() -> dict[str, Any]:
    samples: list[dict[str, str]] = []
    for file in (ROOT / "samples").glob("*/*.csv"):
        samples.append(
            {
                "name": file.stem,
                "path": str(file.relative_to(ROOT)),
                "text": file.read_text(),
            }
        )
    return {"samples": samples}


@router.get("/policies")
def get_policies(template_type: str | None = None) -> dict[str, Any]:
    return {"policies": list_policies(template_type=template_type)}


@router.post("/policies", status_code=201)
def post_policy(payload: PolicyUpsertRequest) -> dict[str, Any]:
    return {"policy": upsert_policy(payload.model_dump())}


@router.post("/import/csv", status_code=201)
def import_csv(payload: CsvImportRequest) -> dict[str, Any]:
    rows = parse_csv_text(payload.csv_text)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV input is empty or invalid.")
    ids = [
        insert_case_and_analysis(row, payload.template_type, payload.source_type, payload.workspace_id)
        for row in rows
    ]
    return {"imported": len(ids), "case_ids": ids}


@router.post("/reviews", status_code=201)
def post_review(payload: ReviewRequest) -> dict[str, Any]:
    return create_review(payload.model_dump())
