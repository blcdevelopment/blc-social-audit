from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.shared.audit_states import AuditStatus
from apps.shared.config import Settings
from apps.shared.models import AuditJob, Base
from apps.worker import tasks
from apps.worker.stages.crawler import CrawledPage, CrawlResult, RobotsPolicy


def _fake_crawler(url: str, settings: Settings, audit_id: str | None) -> CrawlResult:
    now = datetime.now(UTC).isoformat()
    page = CrawledPage(
        url=url,
        final_url="https://example.com/",
        status_code=200,
        title="Example Builder",
        html="""
        <html>
          <head>
            <title>Example Builder Website</title>
            <meta name="description" content="Custom builder serving local homeowners." />
          </head>
          <body>
            <h1>Example Builder</h1>
            <a class="btn cta" href="/estimate">Request Estimate</a>
            <img src="/home.jpg" alt="Finished custom home" />
          </body>
        </html>
        """,
        text="Example Builder Request Estimate",
        fetched_at=now,
    )
    return CrawlResult(
        requested_url=url,
        start_url=url,
        final_url="https://example.com/",
        status="complete",
        pages=[page],
        discovered_links=[],
        skipped_pages=[],
        failed_pages=[],
        robots=RobotsPolicy(status="disabled", robots_url=None),
        started_at=now,
        completed_at=now,
        max_pages=settings.crawler_max_pages,
        user_agent=settings.crawler_user_agent,
    )


def _fake_psi(urls: list[str], settings: Settings) -> dict:
    return {
        "status": "skipped",
        "reason": "unit_test",
        "homepage_url": urls[0],
        "pages_requested": len(urls),
        "pages_analyzed": 0,
        "pages": [],
        "strategies": {},
    }


def test_run_collection_audit_persists_epic_2_artifacts(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(tasks, "SessionLocal", TestingSession)
    monkeypatch.setattr(
        tasks,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            google_psi_api_key=None,
            crawler_screenshots_enabled=False,
        ),
    )

    with TestingSession() as db:
        job = AuditJob(
            url="https://example.com/",
            status=AuditStatus.QUEUED.value,
            current_stage="Queued",
            progress_pct=0,
        )
        db.add(job)
        db.commit()
        job_id = str(job.id)

    tasks.run_collection_audit(job_id, crawler=_fake_crawler, psi_collector=_fake_psi)

    with TestingSession() as db:
        job = db.get(AuditJob, job_id)
        assert job is not None
        assert job.status == AuditStatus.COMPLETE.value
        assert job.current_stage == "Audit scoring and commentary complete"
        assert job.progress_pct == 100
        assert job.result is not None
        assert job.result.crawled_pages["summary"]["successful_pages"] == 1
        assert job.result.psi_facts["status"] == "skipped"
        assert job.result.psi_facts["pages_requested"] == 1
        assert job.result.seo_facts["pages_analyzed"] == 1
        assert job.result.uxui_facts["summary"]["total_ctas"] == 1
        assert job.result.seo_score > 0
        assert job.result.uxui_score > 0
        assert job.result.lead_gen_score > 0
        assert job.result.score_breakdown["status"] == "complete"
        assert job.result.commentary["status"] == "fallback_missing_api_key"
        assert job.result.validation_log["status"] == "complete"
