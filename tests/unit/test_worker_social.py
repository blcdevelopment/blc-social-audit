import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.shared.config import Settings
from apps.shared.models import AuditJob, Base
from apps.worker import tasks
from apps.worker.stages.social.extractor import extract_social_facts

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
NOW = datetime(2026, 6, 23, tzinfo=UTC)


def test_social_audit_runs_end_to_end(tmp_path, monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    monkeypatch.setattr(tasks, "SessionLocal", TestingSession)
    monkeypatch.setattr(
        tasks, "get_settings", lambda: Settings(local_report_storage_dir=tmp_path / "reports")
    )

    strong = json.loads((FIXTURES / "social_instagram_strong.json").read_text())

    def fake_collector(settings, handles):
        # Stand in for the Apify network call; return normalized facts from the fixture.
        return extract_social_facts(
            [{"platform": "instagram", "handle": "acme", "raw": strong}], now=NOW
        )

    with TestingSession() as db:
        job = AuditJob(
            url="https://www.instagram.com/acme/",
            audit_type="social",
            social_handles={"instagram": "acme"},
            status="queued",
            current_stage="Queued",
            progress_pct=0,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = str(job.id)

    tasks.run_collection_audit(job_id, social_collector=fake_collector)

    with TestingSession() as db:
        job = db.get(AuditJob, UUID(job_id))
        assert job.status == "complete"
        assert job.progress_pct == 100
        result = job.result
        assert result is not None
        # Standalone Social Score is populated; website scores stay empty for a social audit.
        assert result.social_score is not None and result.social_score >= 85
        assert result.seo_score is None
        assert result.lead_gen_score is None
        assert result.score_breakdown["category"]["category"] == "social"
        # A real branded PDF was rendered to local storage.
        assert result.pdf_path and Path(result.pdf_path).exists()
        assert Path(result.pdf_path).read_bytes().startswith(b"%PDF")
