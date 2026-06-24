import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/router";
import { FormEvent, useState } from "react";

import Layout from "../components/Layout";
import { ApiError, createAudit } from "../lib/api";

// Accepts a pasted profile LINK (https://instagram.com/acme/, youtube.com/@acme,
// youtube.com/channel/UC...) or a bare @handle and returns the clean handle/ID. The public
// profile is then read — no login/connection.
function extractHandle(raw: string): string {
  let value = raw.trim();
  if (!value) return "";
  if (/youtube\.com/i.test(value)) {
    const yt = value.match(/youtube\.com\/(?:channel\/|c\/|user\/|@)?([^/?#]+)/i);
    if (yt) value = yt[1];
  } else {
    const match = value.match(/(?:instagram\.com|facebook\.com)\/([^/?#]+)/i);
    if (match) value = match[1];
  }
  return value.replace(/^@/, "").replace(/\/+$/, "").trim();
}

export default function SubmitSocialAuditPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [instagram, setInstagram] = useState("");
  const [facebook, setFacebook] = useState("");
  const [youtube, setYoutube] = useState("");
  const [niche, setNiche] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setApiError(null);

    const handles: Record<string, string> = {};
    if (extractHandle(instagram)) handles.instagram = extractHandle(instagram);
    if (extractHandle(facebook)) handles.facebook = extractHandle(facebook);
    if (extractHandle(youtube)) handles.youtube = extractHandle(youtube);
    if (Object.keys(handles).length === 0) {
      setFormError("Enter at least one Instagram, Facebook, or YouTube handle.");
      return;
    }
    setFormError(null);
    setSubmitting(true);

    try {
      const token = await getToken();
      const created = await createAudit(
        {
          audit_type: "social",
          social_handles: handles,
          niche: niche.trim() || null,
        },
        token,
      );
      router.push(`/audit/${created.job_id}`);
    } catch (error) {
      setApiError(
        error instanceof ApiError
          ? error.message
          : "Something went wrong submitting the audit. Please try again.",
      );
      setSubmitting(false);
    }
  }

  return (
    <Layout title="New Social Audit | BLC">
      <div className="page-narrow">
        <p className="eyebrow">New Social Media Audit</p>
        <h1>Audit a brand&apos;s social presence</h1>
        <p className="lede">
          Paste a public Instagram, Facebook, or YouTube <strong>profile link</strong> (or @handle).
          We read the public profile and score how it&apos;s doing — profile completeness, posting cadence,
          engagement, and lead-capture. No login, no account connection, nothing for the target to
          do. Standalone audit with its own report.
        </p>

        <form className="card form" onSubmit={handleSubmit} noValidate>
          {apiError && (
            <div className="alert alert-danger" role="alert">
              {apiError}
            </div>
          )}

          <div className="field">
            <label htmlFor="instagram">Instagram profile link or @handle</label>
            <input
              id="instagram"
              type="text"
              placeholder="https://instagram.com/yourbrand"
              value={instagram}
              onChange={(event) => {
                setInstagram(event.target.value);
                if (formError) setFormError(null);
              }}
              disabled={submitting}
              autoFocus
            />
          </div>

          <div className="field">
            <label htmlFor="facebook">Facebook page link (optional)</label>
            <input
              id="facebook"
              type="text"
              placeholder="https://facebook.com/yourpage"
              value={facebook}
              onChange={(event) => {
                setFacebook(event.target.value);
                if (formError) setFormError(null);
              }}
              disabled={submitting}
            />
          </div>

          <div className="field">
            <label htmlFor="youtube">YouTube channel link or @handle (optional)</label>
            <input
              id="youtube"
              type="text"
              placeholder="https://youtube.com/@yourchannel"
              value={youtube}
              onChange={(event) => {
                setYoutube(event.target.value);
                if (formError) setFormError(null);
              }}
              disabled={submitting}
            />
          </div>

          {formError && <p className="field-error">{formError}</p>}

          <div className="field">
            <label htmlFor="niche">Niche (optional)</label>
            <input
              id="niche"
              type="text"
              placeholder="e.g. coffee shop, law firm, gym"
              value={niche}
              maxLength={255}
              onChange={(event) => setNiche(event.target.value)}
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
                "Start social audit"
              )}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
}
