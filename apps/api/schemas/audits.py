from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field

from apps.worker.stages.report_payload import ReportPayload


class AuditCreateRequest(BaseModel):
    url: AnyHttpUrl
    niche: str | None = Field(default=None, max_length=255)
    target_audience: str | None = Field(default=None, max_length=255)


class AuditCreateResponse(BaseModel):
    job_id: UUID
    status: str
    status_url: str


class AuditEnrichmentResponse(BaseModel):
    job_id: UUID
    status: str
    current_stage: str | None
    message: str


class AuditStatusResponse(BaseModel):
    job_id: UUID
    url: str
    status: str
    current_stage: str | None
    progress_pct: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    report_available: bool


class AuditListItem(BaseModel):
    job_id: UUID
    url: str
    status: str
    current_stage: str | None
    progress_pct: int
    created_at: datetime
    completed_at: datetime | None
    seo_score: int | None
    uxui_score: int | None
    lead_gen_score: int | None
    report_available: bool


class AuditListResponse(BaseModel):
    audits: list[AuditListItem]


class AuditDetailResponse(BaseModel):
    job_id: UUID
    url: str
    niche: str | None
    target_audience: str | None
    status: str
    current_stage: str | None
    progress_pct: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    report_available: bool
    report: ReportPayload | None = None
