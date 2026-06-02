import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import Layout from "../../components/Layout";
import {
  ApiError,
  AuditDetail,
  ReportSection,
  ScoreCard,
  getAuditDetail,
  reportUrl,
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
  { status: "rendering", label: "Render PDF" },
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
  const { id } = router.query;
  const [detail, setDetail] = useState<AuditDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || typeof id !== "string") return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const data = await getAuditDetail(id as string);
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
  }, [id]);

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
                    <a
                      className="btn btn-primary"
                      href={reportUrl(detail.job_id)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      ⬇ Download PDF report
                    </a>
                  ) : (
                    <span className="muted">PDF report unavailable.</span>
                  )}
                </div>

                <ScoreCards scores={detail.report.scores} />

                {detail.report.executive_summary && (
                  <section className="card">
                    <h3>Executive summary</h3>
                    <p className="summary-text">{detail.report.executive_summary}</p>
                  </section>
                )}

                {detail.report.sections.map((section) => (
                  <SectionBlock key={section.id} section={section} />
                ))}

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
