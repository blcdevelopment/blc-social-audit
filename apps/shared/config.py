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

    # Optional Sentry error reporting (API + worker). Empty DSN => disabled
    # (local dev / tests / QA harness), mirroring the Clerk opt-in pattern.
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = Field(default=0.0, ge=0, le=1)

    # Operational alerting (scripts/health_alert.py, run from cron). Empty webhook =>
    # disabled. Posts a Slack/Discord/generic-webhook message when a threshold is breached.
    alert_webhook_url: SecretStr | None = None
    alert_failed_audits_threshold: int = Field(default=5, ge=1)
    alert_stuck_audit_minutes: int = Field(default=60, ge=5)
    # PostgreSQL backups (scripts/backup_db.py, run from cron) -> timestamped .sql.gz.
    backup_storage_dir: Path = Path("./storage/backups")
    backup_retention_days: int = Field(default=14, ge=0)
    pg_dump_path: str = "pg_dump"

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
    # Optional defense-in-depth allowlist of Clerk user ids (the token `sub`) permitted to use
    # the API. Empty (default) => any validly-signed token from clerk_issuer is accepted. Set it
    # to the comma-separated Clerk user ids of the 5-10 operators (visible in the Clerk dashboard)
    # so a stranger who self-registers on the Clerk instance still can't reach the audit endpoints.
    clerk_allowed_subjects: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: str = "postgresql+psycopg://blc:change-me-local@localhost:5432/blc_website_audit"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    audit_enqueue_enabled: bool = True
    # Hard limit kills the worker process; soft limit raises inside the task so the
    # job can be marked FAILED instead of leaving a row stuck in a non-terminal state.
    # 30-minute hard / 29-minute soft ceiling. Large sites with Screaming Frog and
    # full PageSpeed need the headroom; the per-stage time budgets still keep a single
    # audit from running anywhere near this long on a normal site.
    celery_task_time_limit_seconds: int = Field(default=1800, ge=30)
    celery_task_soft_time_limit_seconds: int = Field(default=1740, ge=15)

    local_report_storage_dir: Path = Path("./storage/reports")
    local_screenshot_storage_dir: Path = Path("./storage/screenshots")
    local_tool_export_storage_dir: Path = Path("./storage/tool_exports")
    # Storage retention: scripts/cleanup_storage.py deletes generated reports,
    # screenshots, and tool exports older than this many days. There is no in-app
    # scheduler (run it from cron on the host); 0 disables cleanup (keep forever).
    storage_retention_days: int = Field(default=90, ge=0)
    # Read-only share links: how long a generated share token stays valid.
    share_link_ttl_days: int = Field(default=7, ge=1, le=365)

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
    # Total wall-clock budget for the PageSpeed stage. PSI runs serially over each
    # crawled page (mobile + desktop); without a budget a slow or rate-limited API can
    # push the whole audit past the Celery soft time limit. When the budget is reached
    # the stage stops issuing new requests and returns the pages collected so far.
    psi_total_budget_seconds: int = Field(default=360, ge=30)

    screaming_frog_enabled: bool = False
    screaming_frog_binary: Path | None = None
    screaming_frog_output_dir: Path = Path("./storage/tool_exports/screaming_frog")
    # Clamped at runtime under the Celery soft time limit (screaming_frog.py)
    # so a slow Screaming Frog crawl degrades gracefully instead of killing the
    # whole audit task.
    screaming_frog_timeout_seconds: int = Field(default=600, ge=30)
    screaming_frog_export_tabs: str = "Internal:All,Response Codes:Client Error (4xx)"

    # Built-in site health sweep (httpx status checks over discovered URLs +
    # sitemap). Runs when Screaming Frog is disabled or unavailable, so the
    # Technical SEO report section works in Docker/production without a
    # licensed desktop tool.
    site_health_enabled: bool = True
    site_health_max_internal_urls: int = Field(default=150, ge=1, le=1000)
    site_health_max_external_urls: int = Field(default=50, ge=0, le=500)
    site_health_check_external_links: bool = True
    site_health_concurrency: int = Field(default=8, ge=1, le=20)
    site_health_request_timeout_seconds: int = Field(default=10, ge=1, le=60)
    site_health_total_budget_seconds: int = Field(default=180, ge=10)
    site_health_sitemap_max_urls: int = Field(default=500, ge=0, le=5000)

    google_oauth_client_id: str = ""
    google_oauth_client_secret: SecretStr | None = None
    # Signs the OAuth `state` parameter (CSRF protection). Optional: when empty,
    # each API process generates an ephemeral secret at startup, which is fine for
    # a single-process deployment; set it explicitly if the API runs replicated.
    google_oauth_state_secret: SecretStr | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/google/search-console/callback"
    google_oauth_success_redirect_url: str = "http://localhost:3000/audits"
    gsc_default_date_range_days: int = Field(default=90, ge=7, le=540)
    gsc_row_limit: int = Field(default=25000, ge=1, le=25000)
    url_inspection_max_urls: int = Field(default=20, ge=0, le=200)

    # Social data provider (Apify) — powers the standalone social audit (free-tier credits)
    # via the Instagram + Facebook actors. Empty token => the social collector skips, like
    # other optional external sources.
    apify_api_token: SecretStr | None = None
    apify_timeout_seconds: int = Field(default=120, ge=10)

    # YouTube Data API v3 — free public-data backend for the social audit (channel stats +
    # recent uploads). A plain API key (no OAuth); empty key => the YouTube collector skips
    # gracefully, like the Apify backends.
    youtube_api_key: SecretStr | None = None
    youtube_timeout_seconds: int = Field(default=30, ge=5)

    crawler_user_agent: str = "BLC-Audit-Bot/1.0 (+https://builderleadconverter.com/audit-bot)"
    crawler_max_pages: int = Field(default=10, ge=1, le=50)
    crawler_concurrency: int = Field(default=3, ge=1, le=10)
    crawler_page_timeout_seconds: int = Field(default=30, ge=1)
    crawler_respect_robots_txt: bool = True
    crawler_screenshots_enabled: bool = True
    crawler_allow_private_hosts: bool = False
    # Request-level SSRF guard: when enabled (default), every sub-resource/redirect the
    # headless browser tries to fetch during rendering is validated against the same
    # private/loopback/link-local/metadata-IP block-list as the page URL, closing the
    # mid-render SSRF gap. Auto-disabled when crawler_allow_private_hosts is true
    # (local dev / QA harness crawls against localhost fixtures).
    crawler_intercept_requests: bool = True
    crawler_chromium_executable_path: Path | None = None

    # Optional advisory accessibility pass (axe-core). Default OFF; mirrors
    # screaming_frog_enabled. When enabled, axe runs DURING the crawl (inside the live
    # page-render window, before the page closes) and its findings are stored separately
    # and rendered as an ADVISORY report section. The results NEVER feed the deterministic
    # scoring path (score_audit reads only seo/uxui/psi/external_seo), so scores stay
    # byte-for-byte reproducible whether this is on or off. When disabled, or if axe.min.js
    # is missing / the scan errors / it times out, the audit completes normally with no
    # advisory section (graceful skip, like a missing PSI key).
    accessibility_advisory_enabled: bool = False
    accessibility_axe_script_path: Path = Path("./vendor/axe-core/axe.min.js")
    accessibility_axe_timeout_seconds: int = Field(default=30, ge=5, le=120)
    accessibility_max_examples_per_issue: int = Field(default=5, ge=1, le=50)
    # color-contrast is the most expensive and least reproducible axe rule (it reads
    # computed styles); ops can disable it while keeping the structural advisory checks.
    accessibility_run_contrast: bool = True

    rubric_seo_path: Path = Path("./rubrics/seo.yaml")
    rubric_uxui_path: Path = Path("./rubrics/uxui.yaml")
    rubric_composite_path: Path = Path("./rubrics/composite.yaml")
    rubric_social_path: Path = Path("./rubrics/social.yaml")
    commentary_system_prompt_path: Path = Path("./prompts/commentary_system.md")
    commentary_user_prompt_path: Path = Path("./prompts/commentary_user.md")
    commentary_social_system_prompt_path: Path = Path("./prompts/commentary_social_system.md")
    commentary_social_user_prompt_path: Path = Path("./prompts/commentary_social_user.md")
    brand_config_path: Path = Path("./brand/blc.yaml")
    report_template_path: Path = Path("./templates/report.html")
    report_css_path: Path = Path("./templates/report.css")
    report_social_template_path: Path = Path("./templates/social_report.html")

    @field_validator(
        "api_cors_origins",
        "clerk_authorized_parties",
        "clerk_allowed_subjects",
        mode="before",
    )
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
