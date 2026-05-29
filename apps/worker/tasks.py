from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from apps.shared.audit_states import AuditStatus
from apps.shared.config import Settings, get_settings
from apps.shared.database import SessionLocal
from apps.shared.models import AuditJob, AuditResult
from apps.worker.celery_app import celery_app
from apps.worker.stages.crawler import CrawlResult, crawl_site_sync
from apps.worker.stages.extractor_seo import extract_seo_facts
from apps.worker.stages.extractor_uxui import extract_uxui_facts
from apps.worker.stages.psi_client import collect_pagespeed_facts

JsonDict = dict[str, Any]
CrawlerFunc = Callable[[str, Settings, str | None], CrawlResult]
PsiCollectorFunc = Callable[[Sequence[str], Settings], JsonDict]


def _mark_job(
    db: Session,
    job: AuditJob,
    status: AuditStatus,
    stage: str,
    progress_pct: int,
    error_message: str | None = None,
) -> None:
    now = datetime.now(UTC)
    if job.started_at is None and status != AuditStatus.QUEUED:
        job.started_at = now
    if status in {AuditStatus.COMPLETE, AuditStatus.FAILED}:
        job.completed_at = now
    job.status = status.value
    job.current_stage = stage
    job.progress_pct = progress_pct
    job.error_message = error_message
    db.commit()
    db.refresh(job)


def _pending_score_breakdown(crawl_result: CrawlResult, psi_facts: JsonDict) -> JsonDict:
    return {
        "status": "pending_p1_e3",
        "reason": "P1-E2 collects facts only; deterministic scoring is implemented in P1-E3.",
        "inputs_available": {
            "crawled_pages": len(crawl_result.pages),
            "psi_status": psi_facts.get("status"),
            "seo_facts": True,
            "uxui_facts": True,
        },
    }


def _psi_page_urls(crawl_result: CrawlResult, fallback_url: str) -> list[str]:
    urls = [page.final_url or page.url for page in crawl_result.pages]
    return urls or [crawl_result.final_url or fallback_url]


def _upsert_collection_result(
    db: Session,
    job: AuditJob,
    settings: Settings,
    crawl_result: CrawlResult,
    psi_facts: JsonDict,
    seo_facts: JsonDict,
    uxui_facts: JsonDict,
) -> None:
    result = job.result
    if result is None:
        result = AuditResult(
            job_id=job.id,
            seo_score=0,
            uxui_score=0,
            lead_gen_score=0,
            crawled_pages={},
            seo_facts={},
            uxui_facts={},
            psi_facts={},
            score_breakdown={},
            commentary={},
            validation_log={},
            report_metadata={},
            pdf_path=None,
            rubric_version="pending-p1-e3",
            llm_model=settings.openai_model or "not_configured",
        )
        db.add(result)

    result.seo_score = 0
    result.uxui_score = 0
    result.lead_gen_score = 0
    result.crawled_pages = crawl_result.to_dict()
    result.seo_facts = seo_facts
    result.uxui_facts = uxui_facts
    result.psi_facts = psi_facts
    result.score_breakdown = _pending_score_breakdown(crawl_result, psi_facts)
    result.commentary = {
        "status": "pending_p1_e3",
        "reason": "OpenAI commentary is intentionally not part of P1-E2.",
    }
    result.validation_log = {
        "status": "pending_p1_e3",
        "unsupported_claims": [],
    }
    result.report_metadata = {
        "status": "pending_p1_e4",
        "renderer": "not_configured",
        "collection_completed_at": datetime.now(UTC).isoformat(),
    }
    result.pdf_path = None
    result.rubric_version = "pending-p1-e3"
    result.llm_model = settings.openai_model or "not_configured"
    db.commit()
    db.refresh(job)


def run_collection_audit(
    job_id: str,
    *,
    crawler: CrawlerFunc = crawl_site_sync,
    psi_collector: PsiCollectorFunc = collect_pagespeed_facts,
) -> None:
    settings = get_settings()
    parsed_job_id = UUID(job_id)

    with SessionLocal() as db:
        job = db.get(AuditJob, parsed_job_id)
        if job is None:
            return

        try:
            _mark_job(db, job, AuditStatus.CRAWLING, "Rendering website pages", 15)
            crawl_result = crawler(job.url, settings, str(job.id))

            _mark_job(
                db,
                job,
                AuditStatus.COLLECTING_PERFORMANCE,
                "Collecting PageSpeed Insights",
                45,
            )
            psi_facts = psi_collector(_psi_page_urls(crawl_result, job.url), settings)

            _mark_job(db, job, AuditStatus.EXTRACTING, "Extracting SEO and UX/UI facts", 70)
            seo_facts = extract_seo_facts(crawl_result.pages)
            uxui_facts = extract_uxui_facts(crawl_result.pages)

            _upsert_collection_result(
                db,
                job,
                settings,
                crawl_result,
                psi_facts,
                seo_facts,
                uxui_facts,
            )
            _mark_job(db, job, AuditStatus.COMPLETE, "Collection pipeline complete", 100)
        except Exception as exc:
            db.rollback()
            failed_job = db.get(AuditJob, parsed_job_id)
            if failed_job is not None:
                _mark_job(
                    db,
                    failed_job,
                    AuditStatus.FAILED,
                    "Audit collection failed",
                    100,
                    str(exc),
                )
            raise


@celery_app.task(name="apps.worker.tasks.run_audit")
def run_audit(job_id: str) -> None:
    run_collection_audit(job_id)
