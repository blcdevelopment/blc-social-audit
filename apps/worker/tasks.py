from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session

from apps.shared.audit_states import AuditStatus
from apps.shared.config import Settings, get_settings
from apps.shared.database import SessionLocal
from apps.shared.models import AuditJob, AuditResult
from apps.worker.celery_app import celery_app
from apps.worker.stages.commentary import generate_commentary, generate_social_commentary
from apps.worker.stages.crawler import CrawlResult, crawl_site_sync
from apps.worker.stages.docx_renderer import DocxRenderResult, render_audit_docx
from apps.worker.stages.external_seo import collect_external_seo_facts, empty_external_seo_facts
from apps.worker.stages.extractor_seo import extract_seo_facts
from apps.worker.stages.extractor_uxui import extract_uxui_facts
from apps.worker.stages.grounding_validator import validate_commentary_grounding
from apps.worker.stages.pdf_renderer import PdfRenderResult, render_audit_pdf, render_social_pdf
from apps.worker.stages.psi_client import collect_pagespeed_facts
from apps.worker.stages.scoring import score_audit, score_social_audit
from apps.worker.stages.social.collector import collect_social_facts
from apps.worker.stages.social.report import compose_social_report_payload

JsonDict = dict[str, Any]
CrawlerFunc = Callable[[str, Settings, str | None], CrawlResult]
PsiCollectorFunc = Callable[[Sequence[str], Settings], JsonDict]
SocialCollectorFunc = Callable[[Settings, "dict[str, str] | None"], JsonDict]


# Seconds held back after external enrichment for scoring, commentary, grounding,
# PDF/DOCX rendering, and persistence, so the whole task finishes inside the Celery
# soft time limit even when the earlier stages ran long.
_PIPELINE_TAIL_RESERVE_SECONDS = 75


def _external_enrichment_deadline(settings: Settings, task_started: float) -> float:
    """Absolute ``time.monotonic()`` deadline by which external SEO enrichment must
    stop, derived from when the task started and the configured soft time limit."""
    soft_limit = getattr(settings, "celery_task_soft_time_limit_seconds", None)
    if not isinstance(soft_limit, int | float):
        return task_started + 600.0
    return task_started + max(60.0, float(soft_limit) - _PIPELINE_TAIL_RESERVE_SECONDS)


def _collect_external_seo_safely(**kwargs: Any) -> JsonDict:
    """External enrichment must never abort an audit.

    The collectors already degrade internally (skip/failed payloads), but any
    unexpected exception here is converted into a failed payload so the audit
    keeps its deterministic core result. Celery's soft time limit is re-raised:
    once it fires the task's remaining budget is gone and the job must fail fast.
    """
    try:
        return collect_external_seo_facts(**kwargs)
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:
        facts = empty_external_seo_facts(reason="collector_error")
        facts["status"] = "failed"
        facts["error"] = " ".join(str(exc).split())[:500]
        return facts


def _collect_accessibility_advisory_safely(
    crawl_result: CrawlResult, settings: Settings
) -> JsonDict:
    """Normalize the advisory axe-core results gathered during the crawl. Advisory-only and
    must never abort an audit (mirrors external SEO). Returns ``{}`` when the pass is disabled,
    when no page produced a result, or on any normalization error. NEVER feeds scoring."""
    if not settings.accessibility_advisory_enabled:
        return {}
    try:
        from apps.worker.stages.accessibility import normalize_accessibility_facts, read_axe_version

        per_page = [
            {"url": page.final_url or page.url, "result": page.axe_results}
            for page in crawl_result.pages
            if getattr(page, "axe_results", None)
        ]
        if not per_page:
            return {}
        return normalize_accessibility_facts(
            per_page,
            max_examples=settings.accessibility_max_examples_per_issue,
            axe_version=read_axe_version(settings.accessibility_axe_script_path),
        )
    except SoftTimeLimitExceeded:
        raise
    except Exception:
        return {}


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


def _psi_page_urls(crawl_result: CrawlResult, fallback_url: str) -> list[str]:
    urls = [page.final_url or page.url for page in crawl_result.pages]
    return urls or [crawl_result.final_url or fallback_url]


def _upsert_audit_result(
    db: Session,
    job: AuditJob,
    crawl_result: CrawlResult,
    psi_facts: JsonDict,
    seo_facts: JsonDict,
    uxui_facts: JsonDict,
    external_seo_facts: JsonDict,
    score_breakdown: JsonDict,
    commentary: JsonDict,
    validation_log: JsonDict,
    accessibility_facts: JsonDict | None = None,
) -> AuditResult:
    result = job.result
    if result is None:
        result = AuditResult(
            job_id=job.id,
            seo_score=score_breakdown["scores"]["seo"],
            uxui_score=score_breakdown["scores"]["uxui"],
            lead_gen_score=score_breakdown["scores"]["lead_gen"],
            crawled_pages={},
            seo_facts={},
            uxui_facts={},
            psi_facts={},
            external_seo_facts={},
            score_breakdown={},
            commentary={},
            validation_log={},
            report_metadata={},
            pdf_path=None,
            rubric_version=score_breakdown["rubric_version"],
            llm_model=str(commentary.get("model") or "not_configured"),
        )
        db.add(result)

    result.seo_score = score_breakdown["scores"]["seo"]
    result.uxui_score = score_breakdown["scores"]["uxui"]
    result.lead_gen_score = score_breakdown["scores"]["lead_gen"]
    result.crawled_pages = crawl_result.to_dict()
    result.seo_facts = seo_facts
    result.uxui_facts = uxui_facts
    result.psi_facts = psi_facts
    result.external_seo_facts = external_seo_facts
    # Advisory-only; stored separately from the scored facts. Empty => NULL => no report section.
    result.accessibility_facts = accessibility_facts or None
    result.score_breakdown = score_breakdown
    result.commentary = commentary
    result.validation_log = validation_log
    result.report_metadata = {
        "status": "pending_pdf_render",
        "renderer": "weasyprint",
        "collection_completed_at": datetime.now(UTC).isoformat(),
        "scoring_completed": True,
        "commentary_provider": commentary.get("provider"),
    }
    result.pdf_path = None
    result.rubric_version = score_breakdown["rubric_version"]
    result.llm_model = str(commentary.get("model") or "not_configured")
    db.commit()
    db.refresh(result)
    db.refresh(job)
    return result


def _store_export_results(
    db: Session,
    result: AuditResult,
    pdf_result: PdfRenderResult,
    docx_result: DocxRenderResult | None,
    docx_error: str | None = None,
) -> None:
    docx_metadata: JsonDict
    if docx_result is not None:
        docx_metadata = docx_result.report_metadata
    else:
        docx_metadata = {"status": "failed", "error": docx_error or "docx render failed"}
    result.report_metadata = {
        **pdf_result.report_metadata,
        "exports": {
            "pdf": pdf_result.report_metadata,
            "docx": docx_metadata,
        },
        "docx_path": docx_result.docx_path if docx_result else None,
        "docx_size_bytes": docx_result.size_bytes if docx_result else 0,
    }
    result.pdf_path = pdf_result.pdf_path
    db.commit()
    db.refresh(result)


def _render_docx_safely(job: AuditJob, result: AuditResult, settings: Settings):
    """The PDF is the primary deliverable; a DOCX failure must not fail the audit."""
    try:
        return render_audit_docx(job, result, settings), None
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:
        return None, " ".join(str(exc).split())[:500]


def _page_urls_from_crawled_pages(crawled_pages: JsonDict, fallback_url: str) -> list[str]:
    pages = crawled_pages.get("pages")
    if not isinstance(pages, list):
        return [fallback_url]

    urls = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        url = page.get("final_url") or page.get("url")
        if url:
            urls.append(str(url))
    return urls or [fallback_url]


def _upsert_social_result(
    db: Session,
    job: AuditJob,
    social_facts: JsonDict,
    social_result: JsonDict,
) -> AuditResult:
    rubric_version = str(social_result.get("rubric_version") or "phase2-social")
    result = job.result
    if result is None:
        result = AuditResult(
            job_id=job.id,
            seo_score=None,
            uxui_score=None,
            lead_gen_score=None,
            crawled_pages={},
            seo_facts={},
            uxui_facts={},
            psi_facts={},
            external_seo_facts={},
            score_breakdown={},
            commentary={},
            validation_log={},
            report_metadata={},
            pdf_path=None,
            rubric_version=rubric_version,
            llm_model="deterministic",
        )
        db.add(result)

    result.seo_score = None
    result.uxui_score = None
    result.lead_gen_score = None
    result.social_score = social_result.get("score")
    result.social_facts = social_facts
    result.score_breakdown = social_result
    result.report_metadata = {
        "status": "pending_pdf_render",
        "renderer": "weasyprint",
        "report_kind": "social",
    }
    result.pdf_path = None
    result.rubric_version = rubric_version
    result.llm_model = "deterministic"
    db.commit()
    db.refresh(result)
    db.refresh(job)
    return result


def _run_social_pipeline(
    db: Session,
    job: AuditJob,
    settings: Settings,
    social_collector: SocialCollectorFunc,
) -> None:
    _mark_job(db, job, AuditStatus.CRAWLING, "Collecting social profiles", 40)
    social_facts = social_collector(settings, job.social_handles)

    _mark_job(db, job, AuditStatus.SCORING, "Scoring social profiles", 80)
    social_result = score_social_audit(social_facts, settings)

    result = _upsert_social_result(db, job, social_facts, social_result)

    _mark_job(db, job, AuditStatus.COMMENTING, "Writing social commentary", 88)
    baseline = compose_social_report_payload(job, result)
    commentary = generate_social_commentary(
        audit_context={"handles": job.social_handles, "niche": job.niche},
        social_facts=social_facts,
        score=baseline.get("score"),
        findings=baseline.get("findings") or [],
        settings=settings,
    )
    result.commentary = commentary
    result.llm_model = commentary.get("model") or result.llm_model
    db.commit()
    db.refresh(result)

    _mark_job(db, job, AuditStatus.RENDERING, "Rendering social report", 95)
    pdf_result = render_social_pdf(job, result, settings)
    result.report_metadata = {
        **pdf_result.report_metadata,
        "exports": {"pdf": pdf_result.report_metadata},
    }
    result.pdf_path = pdf_result.pdf_path
    db.commit()
    db.refresh(result)

    _mark_job(db, job, AuditStatus.COMPLETE, "Social audit complete", 100)


def run_collection_audit(
    job_id: str,
    *,
    crawler: CrawlerFunc = crawl_site_sync,
    psi_collector: PsiCollectorFunc = collect_pagespeed_facts,
    social_collector: SocialCollectorFunc = collect_social_facts,
) -> None:
    settings = get_settings()
    task_started = time.monotonic()
    parsed_job_id = UUID(job_id)

    with SessionLocal() as db:
        job = db.get(AuditJob, parsed_job_id)
        if job is None:
            return

        # Idempotency: a redelivered task (worker crash + acks_late re-queue) must not re-run and
        # overwrite an audit that already finished. Re-running a queued/in-progress job is fine —
        # that is the crash recovery acks_late buys us.
        if (job.status or "") == AuditStatus.COMPLETE.value:
            return

        try:
            if (job.audit_type or "website") == "social":
                _run_social_pipeline(db, job, settings, social_collector)
                return

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
            # Advisory-only; computed from axe results gathered during the crawl. Deliberately
            # NOT passed to score_audit / generate_commentary below, so scores are identical
            # whether this opt-in pass ran or not.
            accessibility_facts = _collect_accessibility_advisory_safely(crawl_result, settings)

            _mark_job(db, job, AuditStatus.EXTRACTING, "Collecting external SEO insights", 76)
            external_seo_facts = _collect_external_seo_safely(
                url=job.url,
                audit_id=str(job.id),
                page_urls=_psi_page_urls(crawl_result, job.url),
                settings=settings,
                db=db,
                seo_facts=seo_facts,
                crawled_pages=crawl_result.to_dict(),
                rendered_pages=crawl_result.pages,
                deadline=_external_enrichment_deadline(settings, task_started),
            )

            _mark_job(db, job, AuditStatus.SCORING, "Scoring extracted facts", 80)
            score_breakdown = score_audit(
                seo_facts,
                uxui_facts,
                psi_facts,
                settings,
                external_seo_facts=external_seo_facts,
            )

            _mark_job(db, job, AuditStatus.COMMENTING, "Generating grounded commentary", 88)
            commentary = generate_commentary(
                audit_context={
                    "url": job.url,
                    "niche": job.niche,
                    "target_audience": job.target_audience,
                },
                seo_facts=seo_facts,
                uxui_facts=uxui_facts,
                psi_facts=psi_facts,
                external_seo_facts=external_seo_facts,
                score_breakdown=score_breakdown,
                settings=settings,
            )

            _mark_job(db, job, AuditStatus.VALIDATING, "Validating commentary grounding", 95)
            commentary, validation_log = validate_commentary_grounding(
                commentary,
                fact_sources={
                    "seo_facts": seo_facts,
                    "uxui_facts": uxui_facts,
                    "psi_facts": psi_facts,
                    "external_seo_facts": external_seo_facts,
                    # Only the headline scores are citable numbers. The full score
                    # breakdown's rule weights, params, and ratios are internal scoring
                    # mechanics and must not count as "grounding" for LLM numeric claims.
                    "scores": score_breakdown.get("scores", {}),
                },
            )

            result = _upsert_audit_result(
                db,
                job,
                crawl_result,
                psi_facts,
                seo_facts,
                uxui_facts,
                external_seo_facts,
                score_breakdown,
                commentary,
                validation_log,
                accessibility_facts=accessibility_facts,
            )

            _mark_job(db, job, AuditStatus.RENDERING, "Rendering report exports", 98)
            pdf_result = render_audit_pdf(job, result, settings)
            docx_result, docx_error = _render_docx_safely(job, result, settings)
            _store_export_results(db, result, pdf_result, docx_result, docx_error)

            _mark_job(db, job, AuditStatus.COMPLETE, "Audit report complete", 100)
        except SoftTimeLimitExceeded:
            # The soft time limit fired: mark the job FAILED with an honest reason (not an empty
            # exception repr), then re-raise so Celery records + acks it (no redelivery loop).
            db.rollback()
            timed_out = db.get(AuditJob, parsed_job_id)
            if timed_out is not None:
                _mark_job(
                    db,
                    timed_out,
                    AuditStatus.FAILED,
                    "Audit timed out",
                    timed_out.progress_pct or 0,
                    "Audit exceeded the time limit and was stopped before completing.",
                )
            raise
        except Exception as exc:
            db.rollback()
            failed_job = db.get(AuditJob, parsed_job_id)
            if failed_job is not None:
                _mark_job(
                    db,
                    failed_job,
                    AuditStatus.FAILED,
                    "Audit collection failed",
                    failed_job.progress_pct or 0,
                    str(exc),
                )
            raise


@celery_app.task(name="apps.worker.tasks.run_audit")
def run_audit(job_id: str) -> None:
    run_collection_audit(job_id)


def rerun_external_enrichment_for_audit(job_id: str) -> None:
    settings = get_settings()
    task_started = time.monotonic()
    parsed_job_id = UUID(job_id)

    with SessionLocal() as db:
        job = db.get(AuditJob, parsed_job_id)
        if job is None or job.result is None:
            return

        # Snapshot the fields the rerun overwrites. The enriched values are
        # committed BEFORE the PDF re-renders; if rendering then fails, restoring
        # this snapshot keeps the stored scores consistent with the PDF the
        # operator can still download.
        previous = {
            "external_seo_facts": job.result.external_seo_facts,
            "score_breakdown": job.result.score_breakdown,
            "commentary": job.result.commentary,
            "validation_log": job.result.validation_log,
            "seo_score": job.result.seo_score,
            "uxui_score": job.result.uxui_score,
            "lead_gen_score": job.result.lead_gen_score,
            "rubric_version": job.result.rubric_version,
            "llm_model": job.result.llm_model,
            "report_metadata": job.result.report_metadata,
        }

        try:
            result = job.result
            _mark_job(db, job, AuditStatus.EXTRACTING, "Collecting external SEO insights", 76)
            crawled_pages = result.crawled_pages or {}
            page_urls = _page_urls_from_crawled_pages(crawled_pages, job.url)
            external_seo_facts = _collect_external_seo_safely(
                url=job.url,
                audit_id=str(job.id),
                page_urls=page_urls,
                settings=settings,
                db=db,
                seo_facts=result.seo_facts or {},
                crawled_pages=crawled_pages,
                rendered_pages=None,
                deadline=_external_enrichment_deadline(settings, task_started),
            )

            _mark_job(db, job, AuditStatus.SCORING, "Rescoring enriched audit facts", 82)
            seo_facts = result.seo_facts or {}
            uxui_facts = result.uxui_facts or {}
            psi_facts = result.psi_facts or {}
            score_breakdown = score_audit(
                seo_facts,
                uxui_facts,
                psi_facts,
                settings,
                external_seo_facts=external_seo_facts,
            )

            _mark_job(db, job, AuditStatus.COMMENTING, "Refreshing grounded commentary", 88)
            commentary = generate_commentary(
                audit_context={
                    "url": job.url,
                    "niche": job.niche,
                    "target_audience": job.target_audience,
                },
                seo_facts=seo_facts,
                uxui_facts=uxui_facts,
                psi_facts=psi_facts,
                external_seo_facts=external_seo_facts,
                score_breakdown=score_breakdown,
                settings=settings,
            )

            _mark_job(db, job, AuditStatus.VALIDATING, "Validating refreshed commentary", 95)
            commentary, validation_log = validate_commentary_grounding(
                commentary,
                fact_sources={
                    "seo_facts": seo_facts,
                    "uxui_facts": uxui_facts,
                    "psi_facts": psi_facts,
                    "external_seo_facts": external_seo_facts,
                    "scores": score_breakdown.get("scores", {}),
                },
            )

            result.external_seo_facts = external_seo_facts
            result.score_breakdown = score_breakdown
            result.commentary = commentary
            result.validation_log = validation_log
            result.seo_score = score_breakdown["scores"]["seo"]
            result.uxui_score = score_breakdown["scores"]["uxui"]
            result.lead_gen_score = score_breakdown["scores"]["lead_gen"]
            result.rubric_version = score_breakdown["rubric_version"]
            result.llm_model = str(commentary.get("model") or "not_configured")
            result.report_metadata = {
                **(result.report_metadata or {}),
                "status": "pending_export_render",
                "collection_completed_at": datetime.now(UTC).isoformat(),
                "external_enrichment_completed": True,
                "commentary_provider": commentary.get("provider"),
            }
            db.commit()
            db.refresh(result)

            _mark_job(db, job, AuditStatus.RENDERING, "Rendering enriched report exports", 98)
            pdf_result = render_audit_pdf(job, result, settings)
            docx_result, docx_error = _render_docx_safely(job, result, settings)
            _store_export_results(db, result, pdf_result, docx_result, docx_error)

            _mark_job(db, job, AuditStatus.COMPLETE, "Audit report complete", 100)
        except Exception as exc:
            db.rollback()
            failed_job = db.get(AuditJob, parsed_job_id)
            if failed_job is not None and failed_job.result is not None:
                # The original audit result and report still exist — a failed
                # enrichment rerun must not flip a COMPLETE audit to FAILED.
                # Restore the snapshot so the stored scores/commentary match the
                # report the operator can still download (the mid-rerun commit may
                # have already persisted enriched values the PDF never rendered).
                for field, value in previous.items():
                    setattr(failed_job.result, field, value)
                _mark_job(
                    db,
                    failed_job,
                    AuditStatus.COMPLETE,
                    "External SEO enrichment failed; previous report kept",
                    100,
                    str(exc),
                )
            elif failed_job is not None:
                _mark_job(
                    db,
                    failed_job,
                    AuditStatus.FAILED,
                    "External SEO enrichment failed",
                    failed_job.progress_pct or 0,
                    str(exc),
                )
            raise


@celery_app.task(name="apps.worker.tasks.rerun_external_enrichment")
def rerun_external_enrichment(job_id: str) -> None:
    rerun_external_enrichment_for_audit(job_id)
