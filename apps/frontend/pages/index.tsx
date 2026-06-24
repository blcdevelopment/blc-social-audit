import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/router";
import { FormEvent, useState } from "react";

import Layout from "../components/Layout";
import SearchConsoleIntegration from "../components/SearchConsoleIntegration";
import { ApiError, createAudit } from "../lib/api";

function normalizeUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return trimmed;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function isValidUrl(value: string): boolean {
  if (/\s/.test(value)) return false;
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
  // Require a dotted public host (example.com) or localhost so obvious typos are caught inline.
  return parsed.hostname === "localhost" || parsed.hostname.includes(".");
}

export default function SubmitAuditPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [url, setUrl] = useState("");
  const [niche, setNiche] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setApiError(null);

    const candidate = normalizeUrl(url);
    if (!candidate) {
      setUrlError("Enter the website URL you want to audit.");
      return;
    }
    if (!isValidUrl(candidate)) {
      setUrlError("Enter a valid website URL, e.g. https://example.com");
      return;
    }
    setUrlError(null);
    setSubmitting(true);

    try {
      const token = await getToken();
      const created = await createAudit(
        {
          url: candidate,
          niche: niche.trim() || null,
          target_audience: targetAudience.trim() || null,
        },
        token,
      );
      router.push(`/audit/${created.job_id}`);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Something went wrong submitting the audit. Please try again.";
      setApiError(message);
      setSubmitting(false);
    }
  }

  return (
    <Layout title="New Audit | BLC Website Audit">
      <div className="page-narrow">
        <p className="eyebrow">New Website Audit</p>
        <h1>Submit a website for auditing</h1>
        <p className="lede">
          Enter a website URL to run the full SEO, UX/UI, and lead generation readiness audit.
          Niche and target audience are optional and help tailor the AI commentary.
        </p>

        <SearchConsoleIntegration />

        <form className="card form" onSubmit={handleSubmit} noValidate>
          {apiError && (
            <div className="alert alert-danger" role="alert">
              {apiError}
            </div>
          )}

          <div className="field">
            <label htmlFor="url">
              Website URL <span className="required">*</span>
            </label>
            <input
              id="url"
              name="url"
              type="text"
              inputMode="url"
              placeholder="https://example.com"
              value={url}
              onChange={(event) => {
                setUrl(event.target.value);
                if (urlError) setUrlError(null);
              }}
              aria-invalid={urlError ? "true" : "false"}
              aria-describedby={urlError ? "url-error" : undefined}
              disabled={submitting}
              autoFocus
            />
            {urlError && (
              <p className="field-error" id="url-error">
                {urlError}
              </p>
            )}
          </div>

          <div className="field">
            <label htmlFor="niche">Niche (optional)</label>
            <input
              id="niche"
              name="niche"
              type="text"
              placeholder="e.g. coffee shop, law firm, gym"
              value={niche}
              maxLength={255}
              onChange={(event) => setNiche(event.target.value)}
              disabled={submitting}
            />
          </div>

          <div className="field">
            <label htmlFor="target_audience">Target audience (optional)</label>
            <input
              id="target_audience"
              name="target_audience"
              type="text"
              placeholder="e.g. customers in your area"
              value={targetAudience}
              maxLength={255}
              onChange={(event) => setTargetAudience(event.target.value)}
              disabled={submitting}
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? (
                <>
                  <span className="spinner" aria-hidden="true" /> Submitting…
                </>
              ) : (
                "Start audit"
              )}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
}
