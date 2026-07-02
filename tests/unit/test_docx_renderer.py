from types import SimpleNamespace
from uuid import uuid4
from zipfile import ZipFile

from apps.worker.stages.docx_renderer import render_report_docx
from apps.worker.stages.report_payload import compose_report_payload


def test_render_report_docx_writes_valid_package(tmp_path) -> None:
    payload = compose_report_payload(_job(), _result())
    output_path = tmp_path / "audit.docx"

    result = render_report_docx(payload, output_path=output_path)

    assert result.docx_path == str(output_path)
    assert result.size_bytes > 0
    with ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert "[Content_Types].xml" in names
        assert "word/document.xml" in names
        document = archive.read("word/document.xml").decode("utf-8")

    assert "Website Audit Report" in document
    assert "Executive Summary" in document
    assert "How to use it" in document
    assert "Technical SEO" in document
    assert "CTR (click-through rate)" in document
    assert "Google Search Performance" in document
    assert "Lead Generation Roadmap" in document


def test_render_report_docx_appends_benchmark_section(tmp_path) -> None:
    # When a benchmark ran, the DOCX must append the Competitor Benchmarking section too (parity
    # with the PDF) — otherwise the same audit's PDF and DOCX diverge.
    result = _result()
    result.score_breakdown = {
        **result.score_breakdown,
        "benchmark": {
            "status": "complete",
            "provider": "semrush",
            "competitors": [
                {"label": "rival.com", "is_industry": False, "source": "semrush", "seo": 60},
            ],
        },
    }
    payload = compose_report_payload(_job(), result)
    output_path = tmp_path / "audit.docx"

    render_report_docx(payload, output_path=output_path)

    with ZipFile(output_path) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
    assert "Competitor Benchmarking" in document
    assert "rival.com" in document
    assert "Benchmark source: semrush" in document


def test_render_report_docx_omits_benchmark_when_absent(tmp_path) -> None:
    # No benchmark => no section (byte-identical to a plain website DOCX).
    payload = compose_report_payload(_job(), _result())
    output_path = tmp_path / "audit.docx"

    render_report_docx(payload, output_path=output_path)

    with ZipFile(output_path) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
    assert "Competitor Benchmarking" not in document


def _job() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        url="https://example.com/",
        niche="builder",
        target_audience="homeowners",
    )


def _result() -> SimpleNamespace:
    return SimpleNamespace(
        seo_score=76,
        uxui_score=68,
        lead_gen_score=72,
        crawled_pages={
            "status": "complete",
            "requested_url": "https://example.com/",
            "final_url": "https://example.com/",
            "summary": {"successful_pages": 2, "failed_pages": 0, "skipped_pages": 0},
        },
        seo_facts={},
        uxui_facts={},
        psi_facts={"status": "skipped", "summary": {}},
        score_breakdown={"scores": {"seo": 76, "uxui": 68, "lead_gen": 72}},
        commentary={"content": {"executive_summary": "The site has clear opportunities."}},
        validation_log={"status": "complete"},
        report_metadata={},
        pdf_path=None,
        rubric_version="phase1-test",
        llm_model="deterministic",
    )
