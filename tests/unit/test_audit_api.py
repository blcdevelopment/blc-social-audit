from collections.abc import Generator
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_db_session
from apps.api.main import app
from apps.api.routes import audits as audit_routes
from apps.shared.models import Base


def test_swagger_ui_is_available() -> None:
    client = TestClient(app)

    root_response = client.get("/", follow_redirects=False)
    assert root_response.status_code in {307, 308}
    assert root_response.headers["location"] == "/docs"

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"]["title"] == "BLC Website Audit Automation"


def test_create_and_read_audit_lifecycle(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_db() -> Generator[Session, None, None]:
        with TestingSession() as db:
            yield db

    monkeypatch.setattr(
        audit_routes,
        "get_settings",
        lambda: SimpleNamespace(audit_enqueue_enabled=False),
    )
    app.dependency_overrides[get_db_session] = override_db

    try:
        client = TestClient(app)
        create_response = client.post(
            "/audits",
            json={
                "url": "https://example.com",
                "niche": "builder",
                "target_audience": "homeowners",
            },
        )

        assert create_response.status_code == 201
        payload = create_response.json()
        assert payload["status"] == "queued"

        status_response = client.get(payload["status_url"])
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["url"] == "https://example.com/"
        assert status_payload["progress_pct"] == 0
        assert status_payload["report_available"] is False

        list_response = client.get("/audits")
        assert list_response.status_code == 200
        assert len(list_response.json()["audits"]) == 1
    finally:
        app.dependency_overrides.clear()
