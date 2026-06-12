from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from apps.api.auth import require_user
from apps.api.deps import get_db_session
from apps.api.schemas.audits import (
    AuditCreateRequest,
    AuditCreateResponse,
    AuditDetailResponse,
    AuditEnrichmentResponse,
    AuditListItem,
    AuditListResponse,
    AuditStatusResponse,
)
from apps.shared.audit_states import AuditStatus
from apps.shared.config import get_settings
from apps.shared.models import AuditJob
from apps.worker.stages.docx_renderer import render_audit_docx
from apps.worker.stages.report_payload import compose_report_payload

# Every audit endpoint requires a valid Clerk session (no-op when CLERK_ISSUER is unset).
router = APIRouter(prefix="/audits", tags=["audits"], dependencies=[Depends(require_user)])
DbSession = Annotated[Session, Depends(get_db_session)]
AuditLimit = Annotated[int, Query(ge=1, le=100)]
AuditOffset = Annotated[int, Query(ge=0)]


def _report_available(job: AuditJob) -> bool:
    return bool(job.result and job.result.pdf_path and Path(job.result.pdf_path).exists())


def _report_recorded(job: AuditJob) -> bool:
    # Cheap, DB-only check for list views: avoids a filesystem stat per row (which would
    # become a network round-trip per row once reports move to object storage). The
    # download endpoint remains the source of truth and 404s if the file is gone.
    return bool(job.result and job.result.pdf_path)


def _docx_path(job: AuditJob) -> Path | None:
    if not job.result:
        return None
    metadata = job.result.report_metadata or {}
    path = metadata.get("docx_path") if isinstance(metadata, dict) else None
    return Path(path) if isinstance(path, str) and path else None


def _status_response(job: AuditJob) -> AuditStatusResponse:
    return AuditStatusResponse(
        job_id=job.id,
        url=job.url,
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        report_available=_report_available(job),
    )


def _detail_response(job: AuditJob) -> AuditDetailResponse:
    report = None
    if job.result is not None:
        report = compose_report_payload(job, job.result)
    return AuditDetailResponse(
        job_id=job.id,
        url=job.url,
        niche=job.niche,
        target_audience=job.target_audience,
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        report_available=_report_available(job),
        report=report,
    )


def _list_item(job: AuditJob) -> AuditListItem:
    result = job.result
    return AuditListItem(
        job_id=job.id,
        url=job.url,
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        created_at=job.created_at,
        completed_at=job.completed_at,
        seo_score=result.seo_score if result else None,
        uxui_score=result.uxui_score if result else None,
        lead_gen_score=result.lead_gen_score if result else None,
        report_available=_report_recorded(job),
    )


@router.post("", response_model=AuditCreateResponse, status_code=status.HTTP_201_CREATED)
def create_audit(
    payload: AuditCreateRequest,
    db: DbSession,
) -> AuditCreateResponse:
    settings = get_settings()
    job = AuditJob(
        url=str(payload.url),
        niche=payload.niche,
        target_audience=payload.target_audience,
        status=AuditStatus.QUEUED.value,
        current_stage="Queued",
        progress_pct=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if settings.audit_enqueue_enabled:
        try:
            from apps.worker.tasks import run_audit

            run_audit.delay(str(job.id))
        except Exception as exc:
            job.status = AuditStatus.FAILED.value
            job.current_stage = "Failed to enqueue"
            job.progress_pct = 100
            job.error_message = str(exc)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Audit job was created but could not be enqueued.",
                    "job_id": str(job.id),
                    "error": str(exc),
                },
            ) from exc

    return AuditCreateResponse(
        job_id=job.id,
        status=job.status,
        status_url=f"/audits/{job.id}/status",
    )


@router.get("", response_model=AuditListResponse)
def list_audits(
    db: DbSession,
    limit: AuditLimit = 25,
    offset: AuditOffset = 0,
) -> AuditListResponse:
    jobs = db.scalars(
        select(AuditJob)
        .options(selectinload(AuditJob.result))
        .order_by(AuditJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AuditListResponse(audits=[_list_item(job) for job in jobs])


@router.get("/{job_id}/status", response_model=AuditStatusResponse)
def get_audit_status(job_id: UUID, db: DbSession) -> AuditStatusResponse:
    job = db.get(AuditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")
    return _status_response(job)


@router.get("/{job_id}", response_model=AuditDetailResponse)
def get_audit_detail(job_id: UUID, db: DbSession) -> AuditDetailResponse:
    job = db.get(AuditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")
    return _detail_response(job)


@router.post("/{job_id}/rerun-enrichment", response_model=AuditEnrichmentResponse)
def rerun_audit_enrichment(job_id: UUID, db: DbSession) -> AuditEnrichmentResponse:
    job = db.get(AuditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")
    if job.result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audit enrichment can only be rerun after baseline audit facts exist.",
        )

    settings = get_settings()
    if settings.audit_enqueue_enabled:
        try:
            from apps.worker.tasks import rerun_external_enrichment

            job.status = AuditStatus.EXTRACTING.value
            job.current_stage = "Queued external SEO enrichment"
            job.progress_pct = 70
            job.error_message = None
            db.commit()
            rerun_external_enrichment.delay(str(job.id))
        except Exception as exc:
            job.status = AuditStatus.FAILED.value
            job.current_stage = "Failed to enqueue enrichment"
            job.progress_pct = 100
            job.error_message = str(exc)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Audit enrichment could not be enqueued.",
                    "job_id": str(job.id),
                    "error": str(exc),
                },
            ) from exc
    else:
        from apps.worker.tasks import rerun_external_enrichment_for_audit

        rerun_external_enrichment_for_audit(str(job.id))
        db.refresh(job)

    return AuditEnrichmentResponse(
        job_id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        message="External SEO enrichment has been queued or started.",
    )


@router.get("/{job_id}/report")
def get_audit_report(job_id: UUID, db: DbSession) -> FileResponse:
    job = db.get(AuditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")
    if not job.result or not job.result.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report has not been generated for this audit yet.",
        )

    pdf_path = Path(job.result.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report file is missing from local storage.",
        )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"blc-website-audit-{job.id}.pdf",
    )


@router.get("/{job_id}/docx")
def get_audit_docx(job_id: UUID, db: DbSession) -> FileResponse:
    job = db.get(AuditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")
    if not job.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DOCX report has not been generated for this audit yet.",
        )

    docx_path = _docx_path(job)
    if docx_path is None or not docx_path.exists():
        docx_result = render_audit_docx(job, job.result, get_settings())
        metadata = dict(job.result.report_metadata or {})
        raw_exports = metadata.get("exports")
        exports = dict(raw_exports) if isinstance(raw_exports, dict) else {}
        exports["docx"] = docx_result.report_metadata
        metadata["exports"] = exports
        metadata["docx_path"] = docx_result.docx_path
        metadata["docx_size_bytes"] = docx_result.size_bytes
        job.result.report_metadata = metadata
        db.commit()
        db.refresh(job.result)
        docx_path = Path(docx_result.docx_path)

    return FileResponse(
        docx_path,
        media_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        filename=f"blc-website-audit-{job.id}.docx",
    )
