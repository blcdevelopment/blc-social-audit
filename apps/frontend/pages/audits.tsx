import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Layout from "../components/Layout";
import { ApiError, AuditListItem, listAudits, reportUrl } from "../lib/api";
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
  const [audits, setAudits] = useState<AuditListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listAudits(50);
      setAudits(response.audits);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not load audit history. Try again.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

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
                        <a
                          href={reportUrl(audit.job_id)}
                          className="link-action"
                          target="_blank"
                          rel="noreferrer"
                        >
                          PDF
                        </a>
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
