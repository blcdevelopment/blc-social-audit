from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator

from apps.worker.stages.report_payload import ReportPayload


class BrandOverrides(BaseModel):
    # Per-client white-label overrides applied to the rendered report. All optional;
    # blanks fall back to the default BLC brand (brand/blc.yaml).
    name: str | None = Field(default=None, max_length=120)
    short_name: str | None = Field(default=None, max_length=40)
    primary_color: str | None = Field(default=None, max_length=7)
    accent_color: str | None = Field(default=None, max_length=7)
    logo_url: str | None = Field(default=None, max_length=1000)


class AuditCreateRequest(BaseModel):
    url: AnyHttpUrl | None = None
    audit_type: Literal["website", "social"] = "website"
    niche: str | None = Field(default=None, max_length=255)
    target_audience: str | None = Field(default=None, max_length=255)
    brand_overrides: BrandOverrides | None = None
    # {platform: handle} for social audits, e.g. {"instagram": "acmebuilders"}.
    social_handles: dict[str, str] | None = None

    @model_validator(mode="after")
    def _validate_inputs(self) -> "AuditCreateRequest":
        if self.audit_type == "website" and self.url is None:
            raise ValueError("url is required for a website audit")
        if self.audit_type == "social":
            handles = {k: v for k, v in (self.social_handles or {}).items() if v}
            if not handles:
                raise ValueError("at least one social handle is required for a social audit")
        return self


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
    audit_type: str
    status: str
    current_stage: str | None
    progress_pct: int
    created_at: datetime
    completed_at: datetime | None
    seo_score: int | None
    uxui_score: int | None
    lead_gen_score: int | None
    social_score: int | None
    report_available: bool


class AuditListResponse(BaseModel):
    audits: list[AuditListItem]


class AuditDetailResponse(BaseModel):
    job_id: UUID
    url: str
    audit_type: str
    niche: str | None
    target_audience: str | None
    social_handles: dict[str, str] | None = None
    status: str
    current_stage: str | None
    progress_pct: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    report_available: bool
    seo_score: int | None = None
    uxui_score: int | None = None
    lead_gen_score: int | None = None
    social_score: int | None = None
    report: ReportPayload | None = None
    social_report: dict | None = None


class AuditShareResponse(BaseModel):
    job_id: UUID
    share_token: str
    share_expires_at: datetime
    # Relative path on the API; the UI prepends the API base URL to build the link.
    report_path: str


class AuditShareRevokeResponse(BaseModel):
    job_id: UUID
    shared: bool


class SharedReportResponse(BaseModel):
    job_id: UUID
    url: str
    audit_type: str = "website"
    completed_at: datetime | None
    # A website share carries `report`; a social share carries `social_report`.
    report: ReportPayload | None = None
    social_report: dict | None = None
