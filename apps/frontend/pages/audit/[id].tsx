import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import Layout from "../../components/Layout";
import {
  ApiError,
  AuditDetail,
  ReportFormat,
  ReportSection,
  RoadmapTier,
  ScoreCard,
  downloadReport,
  getAuditDetail,
  rerunAuditEnrichment,
} from "../../lib/api";
import { formatDate, isTerminal, scoreTone, statusLabel, statusTone } from "../../lib/format";

const POLL_INTERVAL_MS = 2500;
const RETRY_INTERVAL_MS = 4000;

const PIPELINE: { status: string; label: string }[] = [
  { status: "queued", label: "Queued" },
  { status: "crawling", label: "Crawl" },
  { status: "collecting_performance", label: "Performance" },
  { status: "extracting", label: "Extract" },
  { status: "scoring", label: "Score" },
  { status: "commenting", label: "Commentary" },
  { status: "validating", label: "Validate" },
  { status: "rendering", label: "Render" },
  { status: "complete", label: "Complete" },
];

function ScoreCards({ scores }: { scores: ScoreCard[] }) {
  return (
    <div className="score-grid">
      {scores.map((card) => (
        <div key={card.id} className={`score-card tone-${scoreTone(card.score)}`}>
          <p className="score-label">{card.label}</p>
          <p className="score-value">
            {card.score}
            <span className="score-max">/ {card.max_score}</span>
          </p>
          <p className="score-desc">{card.description}</p>
        </div>
      ))}
    </div>
  );
}

function SectionBlock({ section }: { section: ReportSection }) {
  return (
    <section className="card section-block">
      <div className="section-head">
        <h3>{section.label}</h3>
        {section.score !== null && (
          <span className={`pill tone-${scoreTone(section.score)}`}>{section.score}/100</span>
        )}
      </div>
      <p className="section-headline">{section.headline}</p>

      {section.findings.length > 0 && (
        <div className="section-sub">
          <h4>Findings</h4>
          <ul className="finding-list">
            {section.findings.map((finding, index) => (
              <li key={index}>
                <span className={`sev sev-${finding.severity}`}>{finding.severity}</span>
                <div>
                  <strong>{finding.title}</strong>
                  <p>{finding.explanation}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {section.recommendations.length > 0 && (
        <div className="section-sub">
          <h4>Recommendations</h4>
          <ul className="rec-list">
            {section.recommendations.map((rec, index) => (
              <li key={index}>
                <strong>{rec.title}</strong>
                <p>{rec.rationale}</p>
                {rec.action_items.length > 0 && (
                  <ul className="action-list">
                    {rec.action_items.map((item, itemIndex) => (
                      <li key={itemIndex}>{item}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function RoadmapBlock({ roadmap }: { roadmap: RoadmapTier[] }) {
  return (
    <section className="card roadmap-block">
      <h3>Lead generation roadmap</h3>
      <div className="roadmap-grid">
        {roadmap.map((tier) => (
          <div key={tier.tier} className="roadmap-tier-ui">
            <h4>{tier.label}</h4>
            {tier.recommendations.length > 0 ? (
              <ol>
                {tier.recommendations.map((recommendation, index) => (
                  <li key={`${recommendation.title}-${index}`}>
                    <strong>{recommendation.title}</strong>
                    <p>{recommendation.rationale}</p>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted">No recommendations generated for this tier.</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function recordNumberText(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  return typeof value === "number" ? String(value) : "N/A";
}

function recordText(record: Record<string, unknown>, key: string, fallback = "N/A"): string {
  const value = record[key];
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return fallback;
}

function ctrText(record: Record<string, unknown>): string {
  const value = record.ctr;
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "N/A";
}

function ExternalSeoBlock({
  report,
}: {
  report: NonNullable<AuditDetail["report"]>;
}) {
  const technical = report.technical_seo_section;
  const search = report.search_performance_section;
  const summary = report.external_seo_summary;
  const technicalAvailable = technical.status === "complete";
  const searchAvailable = search.status === "complete";

  return (
    <section className="card external-seo-block">
      <div className="section-head">
        <div>
          <h3>External SEO intelligence</h3>
          <p className="section-headline">
            Site-wide technical crawl facts and Google Search Console opportunities.
          </p>
        </div>
        <span className="pill">{summary.status}</span>
      </div>

      <div className="external-status-grid">
        <div>
          <span>{summary.technical_crawl_tool || "Technical crawl"}</span>
          <strong>{summary.technical_crawl_status}</strong>
        </div>
        <div>
          <span>Search Console</span>
          <strong>{summary.gsc_status}</strong>
        </div>
        <div>
          <span>URL inspection</span>
          <strong>{summary.url_inspection_status}</strong>
        </div>
        <div>
          <span>Opportunities</span>
          <strong>{searchAvailable ? summary.search_opportunity_count : "N/A"}</strong>
        </div>
      </div>

      <div className="enrichment-grid">
        <div>
          <h4>Technical SEO</h4>
          <p className="muted">
            {technicalAvailable
              ? `${recordNumberText(technical.summary, "urls_crawled")} URLs crawled · ${
                  technical.issues.length
                } issue groups · ${recordNumberText(
                  technical.summary,
                  "non_indexable_internal_urls",
                )} non-indexable`
              : `Status: ${technical.status_label}${
                  technical.reason_label ? ` — ${technical.reason_label}` : ""
                }`}
          </p>
          {technical.notes.map((note) => (
            <p className="muted" key={note}>
              Coverage note: {note}
            </p>
          ))}
          {technicalAvailable && technical.issues.length > 0 ? (
            <table className="insight-table">
              <thead>
                <tr>
                  <th>Issue</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {technical.issues.slice(0, 6).map((issue) => (
                  <tr key={issue.id}>
                    <td>
                      <span className={`sev sev-${issue.severity}`}>{issue.severity}</span>
                      <strong>{issue.title}</strong>
                      <div className="issue-guidance">
                        <p>
                          <b>What it means:</b> {issue.summary}
                        </p>
                        <p>
                          <b>Why it matters:</b> {issue.why_it_matters}
                        </p>
                        <p>
                          <b>Recommended fix:</b> {issue.recommended_fix}
                        </p>
                      </div>
                      {issue.examples.length > 0 && (
                        <div className="issue-locations">
                          <span>{issue.location_label}</span>
                          <ul>
                            {issue.examples.slice(0, 3).map((example) => (
                              <li key={example}>{example}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </td>
                    <td>{issue.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : technicalAvailable ? (
            <p className="muted">
              The technical crawl completed and did not find issue groups that matched the
              report thresholds.
            </p>
          ) : (
            <p className="muted">
              Technical crawl data is not available for this audit, so no clean-or-broken
              technical SEO claims are shown.
            </p>
          )}
        </div>

        <div>
          <h4>Search performance</h4>
          <p className="muted">
            {searchAvailable
              ? `${search.site_url || "Matched Search Console property"} · ${recordNumberText(
                  search.summary,
                  "top_query_count",
                )} queries · ${recordNumberText(search.summary, "top_page_count")} pages`
              : `Status: ${search.status_label}${
                  search.reason_label ? ` — ${search.reason_label}` : ""
                }`}
          </p>
          {searchAvailable && search.ranking_opportunities.length > 0 ? (
            <table className="insight-table">
              <thead>
                <tr>
                  <th>Query</th>
                  <th>Position</th>
                  <th>CTR</th>
                </tr>
              </thead>
              <tbody>
                {search.ranking_opportunities.slice(0, 6).map((row, index) => (
                  <tr key={`${recordText(row, "query")}-${index}`}>
                    <td>{recordText(row, "query")}</td>
                    <td>{recordText(row, "position")}</td>
                    <td>{ctrText(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : searchAvailable ? (
            <p className="muted">
              Search Console completed and did not return ranking opportunities that matched
              the report thresholds.
            </p>
          ) : (
            <p className="muted">Search Console data is not available for this audit.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function ProgressView({ detail }: { detail: AuditDetail }) {
  const currentIndex = PIPELINE.findIndex((step) => step.status === detail.status);
  return (
    <div className="card progress-card">
      <div className="progress-meta">
        <span className="spinner spinner-lg" aria-hidden="true" />
        <div>
          <p className="progress-stage">{detail.current_stage || statusLabel(detail.status)}</p>
          <p className="progress-hint">This page refreshes automatically while the audit runs.</p>
        </div>
        <span className="progress-pct">{detail.progress_pct}%</span>
      </div>
      <div className="progress-track" role="progressbar" aria-valuenow={detail.progress_pct}>
        <div className="progress-fill" style={{ width: `${detail.progress_pct}%` }} />
      </div>
      <ol className="stepper">
        {PIPELINE.map((step, index) => {
          const state =
            currentIndex < 0
              ? "todo"
              : index < currentIndex
                ? "done"
                : index === currentIndex
                  ? "active"
                  : "todo";
          return (
            <li key={step.status} className={`step step-${state}`}>
              <span className="step-dot" aria-hidden="true" />
              {step.label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default function AuditDetailPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { id } = router.query;
  const [detail, setDetail] = useState<AuditDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [enrichmentError, setEnrichmentError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<ReportFormat | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [pollNonce, setPollNonce] = useState(0);

  async function handleDownload(format: ReportFormat) {
    if (!detail) return;
    setDownloadError(null);
    setDownloading(format);
    try {
      const token = await getToken();
      const { blob, filename } = await downloadReport(detail.job_id, format, token);
      const objectUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (error) {
      setDownloadError(
        error instanceof ApiError ? error.message : "Could not download the report.",
      );
    } finally {
      setDownloading(null);
    }
  }

  async function handleRerunEnrichment() {
    if (!detail) return;
    setEnrichmentError(null);
    setEnriching(true);
    try {
      const token = await getToken();
      const response = await rerunAuditEnrichment(detail.job_id, token);
      setDetail({
        ...detail,
        status: response.status,
        current_stage: response.current_stage,
        progress_pct: 70,
      });
      setPollNonce((value) => value + 1);
    } catch (error) {
      setEnrichmentError(
        error instanceof ApiError ? error.message : "Could not rerun external SEO enrichment.",
      );
    } finally {
      setEnriching(false);
    }
  }

  useEffect(() => {
    if (!id || typeof id !== "string") return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const token = await getToken();
        const data = await getAuditDetail(id as string, token);
        if (!active) return;
        setDetail(data);
        setLoadError(null);
        if (!isTerminal(data.status)) {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (error) {
        if (!active) return;
        const apiError = error instanceof ApiError ? error : null;
        if (apiError && apiError.status === 404) {
          setLoadError("This audit could not be found. It may have been removed.");
          return;
        }
        setLoadError(
          apiError?.message || "Could not load the audit status. Retrying automatically…",
        );
        timer = setTimeout(poll, RETRY_INTERVAL_MS);
      }
    }

    poll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [getToken, id, pollNonce]);

  const notFound = loadError && !detail;

  return (
    <Layout title="Audit Detail | BLC Website Audit">
      <div className="page-wide">
        <Link href="/audits" className="back-link">
          ← Back to audit history
        </Link>

        {!detail && !loadError && (
          <div className="card muted-card">
            <span className="spinner" aria-hidden="true" /> Loading audit…
          </div>
        )}

        {notFound && (
          <div className="card">
            <div className="alert alert-danger" role="alert">
              {loadError}
            </div>
            <Link href="/" className="btn btn-secondary">
              Submit a new audit
            </Link>
          </div>
        )}

        {detail && (
          <>
            <div className="detail-header">
              <div>
                <p className="eyebrow">Audit Result</p>
                <h1 className="detail-url">{detail.url}</h1>
                <p className="detail-meta">
                  {detail.niche && <span>Niche: {detail.niche}</span>}
                  {detail.target_audience && <span>Audience: {detail.target_audience}</span>}
                  <span>Submitted: {formatDate(detail.created_at)}</span>
                </p>
              </div>
              <span className={`badge badge-${statusTone(detail.status)}`}>
                {statusLabel(detail.status)}
              </span>
            </div>

            {loadError && detail && (
              <div className="alert alert-warning" role="status">
                {loadError}
              </div>
            )}

            {detail.status === "failed" && (
              <div className="card">
                <div className="alert alert-danger" role="alert">
                  <strong>Audit failed.</strong>
                  <p>{detail.error_message || "The audit pipeline reported an error."}</p>
                </div>
                <Link href="/" className="btn btn-secondary">
                  Try another audit
                </Link>
              </div>
            )}

            {detail.status !== "failed" && !isTerminal(detail.status) && (
              <ProgressView detail={detail} />
            )}

            {detail.status === "complete" && detail.report && (
              <>
                <div className="result-actions card">
                  <div>
                    <h2>Audit complete</h2>
                    <p className="muted">
                      Generated {detail.report.metadata.generated_date} ·{" "}
                      {detail.report.metadata.pages_crawled} pages crawled
                      {detail.report.metadata.failed_pages > 0 &&
                        ` · ${detail.report.metadata.failed_pages} failed`}
                    </p>
                  </div>
                  {detail.report_available ? (
                    <div className="download-buttons">
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleRerunEnrichment}
                        disabled={enriching || detail.status !== "complete"}
                      >
                        {enriching ? "Starting enrichment..." : "Rerun enrichment"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => handleDownload("pdf")}
                        disabled={downloading !== null}
                      >
                        {downloading === "pdf" ? "Downloading PDF..." : "Download PDF"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleDownload("docx")}
                        disabled={downloading !== null}
                      >
                        {downloading === "docx" ? "Downloading DOCX..." : "Download DOCX"}
                      </button>
                    </div>
                  ) : (
                    <span className="muted">Report exports unavailable.</span>
                  )}
                </div>

                {downloadError && (
                  <div className="alert alert-danger" role="alert">
                    {downloadError}
                  </div>
                )}

                {enrichmentError && (
                  <div className="alert alert-danger" role="alert">
                    {enrichmentError}
                  </div>
                )}

                <ScoreCards scores={detail.report.scores} />

                {detail.report.executive_summary && (
                  <section className="card">
                    <h3>Executive summary</h3>
                    <p className="summary-text">{detail.report.executive_summary}</p>
                  </section>
                )}

                <ExternalSeoBlock report={detail.report} />

                {detail.report.sections.map((section) => (
                  <SectionBlock key={section.id} section={section} />
                ))}

                <RoadmapBlock roadmap={detail.report.roadmap} />

                <section className="card meta-grid">
                  <div>
                    <h4>PageSpeed</h4>
                    <p className="muted">
                      {detail.report.pagespeed_summary.status === "complete" ||
                      detail.report.pagespeed_summary.status === "partial"
                        ? `Mobile ${detail.report.pagespeed_summary.avg_mobile_performance ?? "—"} · Desktop ${
                            detail.report.pagespeed_summary.avg_desktop_performance ?? "—"
                          }`
                        : `Status: ${detail.report.pagespeed_summary.status}`}
                    </p>
                  </div>
                  <div>
                    <h4>Commentary validation</h4>
                    <p className="muted">
                      {detail.report.validation_summary.status} ·{" "}
                      {detail.report.validation_summary.numeric_claims_checked} claims checked
                    </p>
                  </div>
                  <div>
                    <h4>Rubric</h4>
                    <p className="muted">{detail.report.metadata.rubric_version}</p>
                  </div>
                  <div>
                    <h4>Commentary model</h4>
                    <p className="muted">{detail.report.metadata.llm_model}</p>
                  </div>
                </section>
              </>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
