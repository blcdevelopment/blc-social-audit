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

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = Field(default=4096, ge=512)
    openai_temperature: float = Field(default=0.2, ge=0, le=1)
    openai_timeout_seconds: int = Field(default=60, ge=1)

    google_psi_api_key: SecretStr | None = None
    psi_scope: Literal["homepage", "all_crawled_pages"] = "all_crawled_pages"
    psi_max_pages: int = Field(default=10, ge=1, le=50)
    psi_timeout_seconds: int = Field(default=60, ge=1)
    psi_max_retries: int = Field(default=3, ge=1)
    psi_cache_ttl_seconds: int = Field(default=86400, ge=0)

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

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("crawler_chromium_executable_path", mode="before")
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
