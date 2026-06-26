from __future__ import annotations

import re
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from pydantic import BaseModel, ConfigDict, Field

from apps.shared.config import Settings
from apps.worker.stages.report_payload import ReportPayload, compose_report_payload

JsonDict = dict[str, Any]
DOCX_RENDERER_VERSION = "phase1-docx-v1"
_INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class DocxRenderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    docx_path: str
    report_metadata: JsonDict
    size_bytes: int = Field(ge=1)


def render_audit_docx(job: Any, result: Any, settings: Settings) -> DocxRenderResult:
    payload = compose_report_payload(job, result)
    output_path = _output_path(settings.local_report_storage_dir, str(job.id))
    return render_report_docx(payload, output_path=output_path)


def render_report_docx(payload: ReportPayload, *, output_path: Path) -> DocxRenderResult:
    rendered_at = datetime.now(UTC)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = {
        "[Content_Types].xml": _content_types(),
        "_rels/.rels": _package_relationships(),
        "docProps/core.xml": _core_properties(payload, rendered_at),
        "docProps/app.xml": _app_properties(),
        "word/document.xml": _document_xml(payload),
        "word/styles.xml": _styles_xml(),
        "word/_rels/document.xml.rels": _empty_relationships(),
    }

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)

    size_bytes = output_path.stat().st_size
    return DocxRenderResult(
        docx_path=str(output_path),
        report_metadata={
            "status": "complete",
            "renderer": "docx_ooxml",
            "renderer_version": DOCX_RENDERER_VERSION,
            "generated_at": rendered_at.isoformat(),
            "docx_path": str(output_path),
            "docx_size_bytes": size_bytes,
        },
        size_bytes=size_bytes,
    )


def _document_xml(payload: ReportPayload) -> str:
    parts: list[str] = []
    metadata = payload.metadata
    parts.append(_paragraph("Website Audit Report", "Title"))
    parts.append(_paragraph(metadata.final_url, "Subtitle"))
    parts.append(_paragraph(f"Generated: {metadata.generated_date}", "Meta"))
    parts.append(_paragraph(f"Pages crawled: {metadata.pages_crawled}", "Meta"))
    if metadata.niche:
        parts.append(_paragraph(f"Niche: {metadata.niche}", "Meta"))
    if metadata.target_audience:
        parts.append(_paragraph(f"Audience: {metadata.target_audience}", "Meta"))

    parts.append(_heading("Executive Summary", 1))
    parts.append(_paragraph(payload.executive_summary))
    for score in payload.scores:
        parts.append(_paragraph(f"{score.label}: {score.score}/{score.max_score}", "Strong"))
        parts.append(_paragraph(score.description))

    for section in payload.sections:
        parts.append(_heading(section.label, 1))
        if section.score is not None:
            parts.append(_paragraph(f"Score: {section.score}/100", "Strong"))
        parts.append(_paragraph(section.headline))
        if section.id == "seo":
            parts.append(
                _paragraph(
                    "How to read this section: SEO findings explain what may keep the site "
                    "from being found, understood, or clicked in search results."
                )
            )
            parts.append(
                _paragraph(
                    "How to use it: Turn each recommendation into a site update, then rerun "
                    "the audit to confirm the same issue no longer appears."
                )
            )
        elif section.id == "uxui":
            parts.append(
                _paragraph(
                    "How to read this section: UX/UI findings explain what may make it harder "
                    "for visitors to trust the page, understand the offer, or take the next step."
                )
            )
            parts.append(
                _paragraph(
                    "How to use it: Prioritize changes that make the primary action easier to "
                    "see, easier to trust, and easier to complete."
                )
            )

        if section.findings:
            parts.append(_heading("Findings", 2))
            for finding in section.findings:
                parts.append(
                    _paragraph(
                        f"{finding.severity.upper()}: {finding.title}",
                        "Strong",
                    )
                )
                parts.append(_paragraph(finding.explanation))

        if section.recommendations:
            parts.append(_heading("Recommendations", 2))
            for recommendation in section.recommendations:
                tier_label = recommendation.tier.replace("_", " ").title()
                parts.append(_paragraph(f"{tier_label}: {recommendation.title}", "Strong"))
                parts.append(_paragraph(recommendation.rationale))
                for item in recommendation.action_items:
                    parts.append(_paragraph(item))

    parts.extend(_external_seo_xml(payload))

    parts.append(_heading("Lead Generation Roadmap", 1))
    for tier in payload.roadmap:
        parts.append(_heading(tier.label, 2))
        if not tier.recommendations:
            parts.append(_paragraph("No recommendations generated for this tier."))
            continue
        for recommendation in tier.recommendations:
            parts.append(_paragraph(recommendation.title, "Strong"))
            parts.append(_paragraph(recommendation.rationale))
            for item in recommendation.action_items:
                parts.append(_paragraph(item))

    parts.append(_heading("Appendix", 1))
    parts.append(_paragraph(payload.appendix.scoring_note))
    parts.append(
        _paragraph(
            "PageSpeed (how fast Google considers the pages, 0-100): "
            f"{payload.pagespeed_summary.status_label}; analyzed "
            f"{payload.pagespeed_summary.pages_analyzed}/"
            f"{payload.pagespeed_summary.pages_requested} pages.",
            "Meta",
        )
    )
    cwv = payload.core_web_vitals
    if cwv.available:
        parts.append(_heading("Core Web Vitals", 2))
        for row in cwv.lab_rows:
            mobile = (
                f"{row.mobile.value_label} ({row.mobile.rating_label})" if row.mobile else "N/A"
            )
            desktop = (
                f"{row.desktop.value_label} ({row.desktop.rating_label})" if row.desktop else "N/A"
            )
            parts.append(_paragraph(f"{row.label} — Mobile: {mobile}; Desktop: {desktop}.", "Meta"))
        if cwv.field_available:
            scope = f" ({cwv.field_source}, {cwv.field_form_factor})" if cwv.field_source else ""
            assessment = ""
            if cwv.field_assessment:
                assessment = f" Overall assessment: {cwv.field_assessment}."
            parts.append(
                _paragraph(f"Real-user field data (Chrome UX Report){scope}.{assessment}", "Meta")
            )
            for metric in cwv.field_metrics:
                parts.append(
                    _paragraph(
                        f"{metric.label} (75th percentile): "
                        f"{metric.value_label} ({metric.rating_label}).",
                        "Meta",
                    )
                )

    parts.append(
        _paragraph(
            "Fact check: every number in the written commentary was checked against the "
            "data collected from the site before this report was generated "
            f"({payload.validation_summary.numeric_claims_checked} numbers checked, "
            f"{payload.validation_summary.unsupported_claim_count} unverified and removed).",
            "Meta",
        )
    )

    # Combined audit only: append the Social Media Audit + Overall Lead-Gen Readiness sections at
    # the VERY END, mirroring the PDF. A website-only audit leaves these None, so the DOCX above
    # is unchanged (byte-identical to before).
    parts.extend(_combined_xml(payload))

    body = "".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}{_section_properties()}</w:body>"
        "</w:document>"
    )


def _external_seo_xml(payload: ReportPayload) -> list[str]:
    parts: list[str] = []
    technical = payload.technical_seo_section
    search = payload.search_performance_section
    technical_available = technical.status == "complete"
    search_available = search.status == "complete"

    parts.append(_heading("Technical SEO", 1))
    parts.append(
        _paragraph(
            f"Status: {technical.status_label}"
            + (f" (source: {technical.tool_label})" if technical.tool_label else "")
            + "; pages analyzed: "
            f"{technical.summary.get('urls_crawled', 'N/A') if technical_available else 'N/A'}.",
            "Meta",
        )
    )
    for note in technical.notes:
        parts.append(_paragraph(f"Coverage note: {note}", "Meta"))
    parts.append(
        _paragraph(
            "What this section tells you: This is the site health check for search engines. "
            "It flags broken links, blocked pages, missing page labels, duplicate metadata, "
            "and image text gaps that can stop Google or visitors from getting the right page."
        )
    )
    parts.append(
        _paragraph(
            "How to use it: Fix high-severity crawl issues first, especially errors on "
            "important service, location, or lead pages. Use the example URLs as the starting "
            "list for the web team or CMS editor."
        )
    )
    if technical_available and technical.issues:
        for issue in technical.issues:
            parts.append(
                _paragraph(
                    f"{issue.severity.upper()}: {issue.title} ({issue.count})",
                    "Strong",
                )
            )
            parts.append(
                _paragraph(f"{issue.summary} {issue.why_it_matters} {issue.recommended_fix}")
            )
            if issue.examples:
                shown = issue.examples[:4]
                if issue.count > len(shown):
                    parts.append(
                        _paragraph(f"Examples ({len(shown)} of {issue.count} affected):", "Meta")
                    )
                else:
                    parts.append(_paragraph("Affected URLs:", "Meta"))
                for example in shown:
                    parts.append(_bullet(example))
    elif technical_available:
        parts.append(
            _paragraph(
                "The technical crawl completed for this audit and did not find issue "
                "groups that matched the report thresholds."
            )
        )
    else:
        reason = f" Reason: {technical.reason_label}" if technical.reason_label else ""
        parts.append(
            _paragraph(
                "Technical crawl data was not available for this report, so this section "
                f"does not make clean-or-broken technical SEO claims.{reason}"
            )
        )

    parts.append(_heading("Google Search Performance", 1))
    parts.append(
        _paragraph(
            f"Status: {search.status_label}; property: {search.site_url or 'N/A'}.",
            "Meta",
        )
    )
    parts.append(
        _paragraph(
            "What this section tells you: Search Console shows how people already find the "
            "site in Google. It highlights pages with visibility but weak clicks, search terms "
            "close to stronger rankings, and pages losing traffic."
        )
    )
    parts.append(
        _paragraph(
            "How to read the numbers: Impressions = how many times the page appeared in "
            "Google results. Clicks = how many times searchers chose it. CTR (click-through "
            "rate) = clicks divided by impressions. Position = the average ranking spot in "
            "the results (1 is the top)."
        )
    )
    if search_available:
        _append_search_rows(
            parts,
            "High-impression, low-CTR pages",
            search.high_impression_low_ctr_pages,
            "page",
        )
        _append_search_rows(
            parts,
            "Queries ranking in positions 4-20",
            search.ranking_opportunities,
            "query",
        )
        _append_search_rows(parts, "Declining pages", search.declining_pages, "page")

    if search.url_inspection_items:
        parts.append(_heading("URL Inspection", 2))
        parts.append(
            _paragraph(
                "This asks Google directly whether each important page is in its index. "
                "'On Google' is Google's answer; the status text is Google's own wording "
                "for how it handled the page.",
                "Meta",
            )
        )
        for item in search.url_inspection_items[:8]:
            parts.append(
                _bullet(
                    f"{item.get('url')}: On Google: {item.get('on_google_label') or 'Unknown'}; "
                    f"Google's status: {item.get('coverage_state') or item.get('status')}"
                )
            )
    elif not search_available:
        parts.append(
            _paragraph(
                "Connect a verified Search Console property and rerun enrichment to populate "
                "Google search performance insights."
            )
        )
    elif (
        not search.high_impression_low_ctr_pages
        and not search.ranking_opportunities
        and not search.declining_pages
    ):
        parts.append(
            _paragraph(
                "Search Console completed for this audit and did not return ranking, CTR, "
                "or decline opportunities that matched the report thresholds."
            )
        )

    return parts


def _append_search_rows(parts: list[str], title: str, rows: list[JsonDict], label_key: str) -> None:
    if not rows:
        return
    parts.append(_heading(title, 2))
    for row in rows[:8]:
        label = row.get(label_key) or row.get("page") or row.get("query") or "Unknown"
        parts.append(
            _bullet(
                f"{label}: clicks={row.get('clicks', row.get('current_clicks', 0))}, "
                f"impressions={row.get('impressions', row.get('current_impressions', 0))}, "
                f"position={row.get('position', 'N/A')}"
            )
        )


def _combined_xml(payload: ReportPayload) -> list[str]:
    """Combined-audit social + overall sections, appended at the end of the website DOCX. Returns
    [] for a website-only audit (social_audit/overall_readiness are None), leaving the DOCX
    unchanged. Mirrors the PDF's appended sections."""
    parts: list[str] = []
    social = payload.social_audit
    overall = payload.overall_readiness

    if social:
        parts.append(_heading("Social Media Audit", 1))
        score = social.get("score")
        score_text = (
            f"Social Score: {score}/100" if score is not None else "Social Score: not available"
        )
        parts.append(_paragraph(score_text, "Strong"))
        parts.append(
            _paragraph(
                "A standalone audit of the brand's public social profiles - profile completeness, "
                "posting cadence, engagement, and lead-capture signals - scored independently of "
                "the website."
            )
        )
        status = social.get("status")
        if status not in ("complete", "partial"):
            parts.append(
                _paragraph(
                    f"Social profiles could not be collected for this audit ({status}), so the "
                    "social score is unavailable."
                )
            )
        else:
            platforms = [p for p in (social.get("platforms") or []) if isinstance(p, dict)]
            if platforms:
                parts.append(_heading("Profiles audited", 2))
                for p in platforms:
                    followers = p.get("followers")
                    ppm = p.get("posts_per_month")
                    eng = p.get("avg_engagement_rate_pct")
                    last = p.get("days_since_last_post")
                    parts.append(
                        _bullet(
                            f"{p.get('platform', '-')} (@{p.get('handle', '-')}): "
                            f"followers={followers if followers is not None else '-'}, "
                            f"posts/mo={ppm if ppm is not None else '-'}, "
                            f"engagement={f'{eng}%' if eng is not None else '-'}, "
                            f"last post={f'{last}d ago' if last is not None else '-'}"
                        )
                    )
            findings = [f for f in (social.get("findings") or []) if isinstance(f, dict)]
            if findings:
                parts.append(_heading("What to improve", 2))
                for f in findings:
                    parts.append(
                        _paragraph(
                            f"{str(f.get('impact', 'medium')).upper()}: {f.get('label', '')}",
                            "Strong",
                        )
                    )
                    if f.get("remediation"):
                        parts.append(_paragraph(f.get("remediation")))
            else:
                parts.append(
                    _paragraph(
                        "No social findings were surfaced - the audited profiles met the "
                        "rubric's checks."
                    )
                )

    if overall and overall.get("score") is not None:
        weights = overall.get("weights") or {}
        inputs = overall.get("inputs") or {}
        web = inputs.get("website_lead_gen")
        soc = inputs.get("social")
        parts.append(_heading("Overall Lead-Gen Readiness", 1))
        parts.append(
            _paragraph(f"Overall Lead-Gen Readiness: {overall.get('score')}/100", "Strong")
        )
        parts.append(
            _paragraph(
                "A single headline score combining the website audit (SEO + UX/UI) and the social "
                "media audit, weighted toward the website because that is where leads are captured."
            )
        )
        parts.append(
            _paragraph(
                f"Website Lead-Gen (SEO + UX/UI): {web if web is not None else '-'} "
                f"(weight {round(weights.get('website', 0) * 100)}%).",
                "Meta",
            )
        )
        parts.append(
            _paragraph(
                f"Social Media: {soc if soc is not None else '-'} "
                f"(weight {round(weights.get('social', 0) * 100)}%).",
                "Meta",
            )
        )
        if overall.get("status") == "website_only":
            parts.append(
                _paragraph(
                    "Social data was unavailable, so this score reflects the website audit only."
                )
            )

    return parts


def _paragraph(text: Any, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}<w:r><w:t>{_xml_text(text)}</w:t></w:r></w:p>"


def _heading(text: Any, level: int) -> str:
    return _paragraph(text, f"Heading{min(max(level, 1), 2)}")


def _bullet(text: Any) -> str:
    return _paragraph(f"- {text}", "ListParagraph")


def _section_properties() -> str:
    return (
        "<w:sectPr>"
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        "</w:sectPr>"
    )


def _styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/></w:rPr>
    <w:pPr><w:spacing w:after="140"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:color w:val="1F74B7"/><w:sz w:val="44"/></w:rPr>
    <w:pPr><w:spacing w:after="220"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:color w:val="5C697A"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:color w:val="1F74B7"/><w:sz w:val="32"/></w:rPr>
    <w:pPr><w:spacing w:before="300" w:after="160"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:color w:val="28864B"/><w:sz w:val="26"/></w:rPr>
    <w:pPr><w:spacing w:before="220" w:after="120"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Strong">
    <w:name w:val="Strong"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Meta">
    <w:name w:val="Meta"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:color w:val="5C697A"/><w:sz w:val="19"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph">
    <w:name w:val="List Paragraph"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:ind w:left="360"/></w:pPr>
  </w:style>
</w:styles>"""


def _content_types() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'wordprocessingml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'extended-properties+xml"/>'
        "</Types>"
    )


def _package_relationships() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/'
        'metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _empty_relationships() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )


def _core_properties(payload: ReportPayload, rendered_at: datetime) -> str:
    title = _xml_text(f"{payload.metadata.site_domain} Website Audit Report")
    timestamp = rendered_at.isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
        'metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{title}</dc:title>"
        "<dc:creator>BLC Website Audit</dc:creator>"
        "<cp:lastModifiedBy>BLC Website Audit</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _app_properties() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>BLC Website Audit</Application>
</Properties>"""


def _xml_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    text = _INVALID_XML_CHARS.sub("", text)
    return escape(text, quote=False)


def _output_path(storage_dir: Path, audit_id: str) -> Path:
    return (storage_dir / f"{audit_id}.docx").resolve()
