import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/router";
import { FormEvent, useState } from "react";

import Layout from "../components/Layout";
import SearchConsoleIntegration from "../components/SearchConsoleIntegration";
import { ApiError, BrandOverrides, createAudit } from "../lib/api";

// Mirrors the backend HEX_COLOR_RE in report_branding.py so the operator gets inline feedback;
// the backend still silently ignores a malformed colour, so this only improves UX.
const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;

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

  // White-label branding (P2-11) — all optional; blanks fall back to the default BLC brand.
  const [brandName, setBrandName] = useState("");
  const [brandShortName, setBrandShortName] = useState("");
  const [brandPrimaryColor, setBrandPrimaryColor] = useState("");
  const [brandAccentColor, setBrandAccentColor] = useState("");
  const [brandLogoUrl, setBrandLogoUrl] = useState("");
  const [brandError, setBrandError] = useState<string | null>(null);

  function buildBrandOverrides(): BrandOverrides | undefined {
    const overrides: BrandOverrides = {};
    if (brandName.trim()) overrides.name = brandName.trim();
    if (brandShortName.trim()) overrides.short_name = brandShortName.trim();
    if (brandPrimaryColor.trim()) overrides.primary_color = brandPrimaryColor.trim();
    if (brandAccentColor.trim()) overrides.accent_color = brandAccentColor.trim();
    if (brandLogoUrl.trim()) overrides.logo_url = brandLogoUrl.trim();
    return Object.keys(overrides).length > 0 ? overrides : undefined;
  }

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

    const badColor = ([
      ["Primary colour", brandPrimaryColor],
      ["Accent colour", brandAccentColor],
    ] as const).find(([, value]) => value.trim() && !HEX_COLOR.test(value.trim()));
    if (badColor) {
      setBrandError(`${badColor[0]} must be a 6-digit hex value, e.g. #1a3a5c.`);
      return;
    }
    setBrandError(null);
    setSubmitting(true);

    try {
      const token = await getToken();
      const created = await createAudit(
        {
          url: candidate,
          niche: niche.trim() || null,
          target_audience: targetAudience.trim() || null,
          brand_overrides: buildBrandOverrides(),
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

          <details className="brand-panel">
            <summary>White-label branding (optional)</summary>
            <p className="muted">
              Override the report logo, name, and colours for a prospect-facing PDF. Leave any
              field blank to keep the default BLC brand.
            </p>
            {brandError && (
              <p className="field-error" role="alert">
                {brandError}
              </p>
            )}

            <div className="field">
              <label htmlFor="brand_name">Brand name</label>
              <input
                id="brand_name"
                name="brand_name"
                type="text"
                placeholder="e.g. Acme Marketing"
                value={brandName}
                maxLength={120}
                onChange={(event) => setBrandName(event.target.value)}
                disabled={submitting}
              />
            </div>

            <div className="field">
              <label htmlFor="brand_short_name">Short name</label>
              <input
                id="brand_short_name"
                name="brand_short_name"
                type="text"
                placeholder="e.g. Acme"
                value={brandShortName}
                maxLength={40}
                onChange={(event) => setBrandShortName(event.target.value)}
                disabled={submitting}
              />
            </div>

            <div className="field">
              <label htmlFor="brand_primary_color">Primary colour (hex)</label>
              <input
                id="brand_primary_color"
                name="brand_primary_color"
                type="text"
                placeholder="#1a3a5c"
                value={brandPrimaryColor}
                maxLength={7}
                onChange={(event) => {
                  setBrandPrimaryColor(event.target.value);
                  if (brandError) setBrandError(null);
                }}
                disabled={submitting}
              />
            </div>

            <div className="field">
              <label htmlFor="brand_accent_color">Accent colour (hex)</label>
              <input
                id="brand_accent_color"
                name="brand_accent_color"
                type="text"
                placeholder="#f5a623"
                value={brandAccentColor}
                maxLength={7}
                onChange={(event) => {
                  setBrandAccentColor(event.target.value);
                  if (brandError) setBrandError(null);
                }}
                disabled={submitting}
              />
            </div>

            <div className="field">
              <label htmlFor="brand_logo_url">Logo URL</label>
              <input
                id="brand_logo_url"
                name="brand_logo_url"
                type="url"
                inputMode="url"
                placeholder="https://cdn.example.com/logo.png"
                value={brandLogoUrl}
                maxLength={1000}
                onChange={(event) => setBrandLogoUrl(event.target.value)}
                disabled={submitting}
              />
            </div>
          </details>

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
