import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Layout from "../components/Layout";
import SearchConsoleIntegration from "../components/SearchConsoleIntegration";
import {
  ApiError,
  AuditListItem,
  ReportFormat,
  downloadReport,
  listAudits,
} from "../lib/api";
import { formatDate, isTerminal, scoreTone, statusLabel, statusTone } from "../lib/format";

function ScoreCell({ score }: { score: number | null }) {
  if (score === null || score === undefined) return <span className="muted">—</span>;
  return <span className={`score-chip tone-${scoreTone(score)}`}>{score}</span>;
}

function RowScores({ audit }: { audit: AuditListItem }) {
  if (audit.status === "failed") return <span className="tag tag-danger">Failed</span>;
  if (!isTerminal(audit.status)) return <span className="tag tag-progress">In progress</span>;
  if (audit.seo_score === null) return <span className="tag tag-neutral">Incomplete</span>;
  return (
    <div className="score-cells">
      <ScoreCell score={audit.lead_gen_score} />
      <ScoreCell score={audit.seo_score} />
      <ScoreCell score={audit.uxui_score} />
    </div>
  );
}

export default function AuditsHistoryPage() {
  const { getToken } = useAuth();
  const [audits, setAudits] = useState<AuditListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const response = await listAudits(50, token);
      setAudits(response.audits);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not load audit history. Try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  async function handleDownload(jobId: string, format: ReportFormat) {
    setError(null);
    setDownloading(`${jobId}:${format}`);
    try {
      const token = await getToken();
      const { blob, filename } = await downloadReport(jobId, format, token);
      const objectUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not download the report.");
    } finally {
      setDownloading(null);
    }
  }

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Layout title="Audit History | BLC Website Audit">
      <div className="page-wide">
        <div className="detail-header">
          <div>
            <p className="eyebrow">Audit History</p>
            <h1>Recent audits</h1>
          </div>
          <div className="header-actions">
            <button type="button" className="btn btn-secondary" onClick={load} disabled={loading}>
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            <Link href="/" className="btn btn-primary">
              New audit
            </Link>
          </div>
        </div>

        {error && (
          <div className="alert alert-danger" role="alert">
            {error}
          </div>
        )}

        <SearchConsoleIntegration />

        {audits === null && !error && (
          <div className="card muted-card">
            <span className="spinner" aria-hidden="true" /> Loading audits…
          </div>
        )}

        {audits !== null && audits.length === 0 && (
          <div className="card empty-state">
            <p>No audits yet.</p>
            <Link href="/" className="btn btn-primary">
              Submit your first audit
            </Link>
          </div>
        )}

        {audits !== null && audits.length > 0 && (
          <div className="card table-card">
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Website</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th>
                    Scores <span className="th-hint">Lead · SEO · UX</span>
                  </th>
                  <th className="col-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {audits.map((audit) => (
                  <tr key={audit.job_id}>
                    <td className="col-url">
                      <Link href={`/audit/${audit.job_id}`} className="url-link">
                        {audit.url}
                      </Link>
                    </td>
                    <td>
                      <span className={`badge badge-${statusTone(audit.status)}`}>
                        {statusLabel(audit.status)}
                      </span>
                    </td>
                    <td className="muted">{formatDate(audit.created_at)}</td>
                    <td>
                      <RowScores audit={audit} />
                    </td>
                    <td className="col-actions">
                      <Link href={`/audit/${audit.job_id}`} className="link-action">
                        Details
                      </Link>
                      {audit.report_available && (
                        <>
                          <button
                            type="button"
                            className="link-action button-link"
                            onClick={() => handleDownload(audit.job_id, "pdf")}
                            disabled={downloading !== null}
                          >
                            {downloading === `${audit.job_id}:pdf` ? "PDF..." : "PDF"}
                          </button>
                          <button
                            type="button"
                            className="link-action button-link"
                            onClick={() => handleDownload(audit.job_id, "docx")}
                            disabled={downloading !== null}
                          >
                            {downloading === `${audit.job_id}:docx` ? "DOCX..." : "DOCX"}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}
