from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "blc-website-audit"
    log_level: str = "info"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"
    api_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # Clerk auth. The API verifies session tokens against this issuer's JWKS.
    # Empty clerk_issuer => API auth is DISABLED (local dev / tests / QA harness);
    # set it in production to require a valid Clerk session on the audit endpoints.
    clerk_issuer: str = ""
    clerk_authorized_parties: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: str = "postgresql+psycopg://blc:change-me-local@localhost:5432/blc_website_audit"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    audit_enqueue_enabled: bool = True
    # Hard limit kills the worker process; soft limit raises inside the task so the
    # job can be marked FAILED instead of leaving a row stuck in a non-terminal state.
    celery_task_time_limit_seconds: int = Field(default=900, ge=30)
    celery_task_soft_time_limit_seconds: int = Field(default=840, ge=15)

    local_report_storage_dir: Path = Path("./storage/reports")
    local_screenshot_storage_dir: Path = Path("./storage/screenshots")
    local_tool_export_storage_dir: Path = Path("./storage/tool_exports")

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = Field(default=4096, ge=512)
    openai_temperature: float = Field(default=0.2, ge=0, le=1)
    openai_timeout_seconds: int = Field(default=60, ge=1)

    # Caps on the deterministic content plan (see content_plan.build_content_plan).
    commentary_max_findings_per_section: int = Field(default=5, ge=1, le=20)
    commentary_max_recommendations_per_section: int = Field(default=5, ge=1, le=20)

    google_psi_api_key: SecretStr | None = None
    psi_scope: Literal["homepage", "all_crawled_pages"] = "all_crawled_pages"
    psi_max_pages: int = Field(default=10, ge=1, le=50)
    psi_timeout_seconds: int = Field(default=60, ge=1)
    psi_max_retries: int = Field(default=3, ge=1)
    psi_cache_ttl_seconds: int = Field(default=86400, ge=0)

    screaming_frog_enabled: bool = False
    screaming_frog_binary: Path | None = None
    screaming_frog_output_dir: Path = Path("./storage/tool_exports/screaming_frog")
    screaming_frog_timeout_seconds: int = Field(default=1800, ge=30)
    screaming_frog_export_tabs: str = "Internal:All,Response Codes:Client Error (4xx)"

    google_oauth_client_id: str = ""
    google_oauth_client_secret: SecretStr | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/google/search-console/callback"
    google_oauth_success_redirect_url: str = "http://localhost:3000/audits"
    gsc_default_date_range_days: int = Field(default=90, ge=7, le=540)
    gsc_row_limit: int = Field(default=25000, ge=1, le=25000)
    url_inspection_max_urls: int = Field(default=20, ge=0, le=200)

    crawler_user_agent: str = "BLC-Audit-Bot/1.0 (+https://builderleadconverter.com/audit-bot)"
    crawler_max_pages: int = Field(default=10, ge=1, le=50)
    crawler_concurrency: int = Field(default=3, ge=1, le=10)
    crawler_page_timeout_seconds: int = Field(default=30, ge=1)
    crawler_respect_robots_txt: bool = True
    crawler_screenshots_enabled: bool = True
    crawler_allow_private_hosts: bool = False
    crawler_chromium_executable_path: Path | None = None

    rubric_seo_path: Path = Path("./rubrics/seo.yaml")
    rubric_uxui_path: Path = Path("./rubrics/uxui.yaml")
    rubric_composite_path: Path = Path("./rubrics/composite.yaml")
    commentary_system_prompt_path: Path = Path("./prompts/commentary_system.md")
    commentary_user_prompt_path: Path = Path("./prompts/commentary_user.md")
    brand_config_path: Path = Path("./brand/blc.yaml")
    report_template_path: Path = Path("./templates/report.html")
    report_css_path: Path = Path("./templates/report.css")

    @field_validator("api_cors_origins", "clerk_authorized_parties", mode="before")
    @classmethod
    def parse_csv_list(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("crawler_chromium_executable_path", "screaming_frog_binary", mode="before")
    @classmethod
    def parse_optional_path(cls, value: str | Path | None) -> str | Path | None:
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_celery_time_limits(self) -> "Settings":
        if self.celery_task_soft_time_limit_seconds >= self.celery_task_time_limit_seconds:
            raise ValueError(
                "celery_task_soft_time_limit_seconds must be less than "
                "celery_task_time_limit_seconds so the soft limit fires first."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
