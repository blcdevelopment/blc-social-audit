// Typed client for the BLC Website Audit API.
// The base URL is configurable so the operator UI can point at a non-local API later.
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

export interface AuditCreateRequest {
  url: string;
  niche?: string | null;
  target_audience?: string | null;
}

export interface AuditCreateResponse {
  job_id: string;
  status: string;
  status_url: string;
}

export interface AuditListItem {
  job_id: string;
  url: string;
  status: string;
  current_stage: string | null;
  progress_pct: number;
  created_at: string;
  completed_at: string | null;
  seo_score: number | null;
  uxui_score: number | null;
  lead_gen_score: number | null;
  report_available: boolean;
}

export interface AuditListResponse {
  audits: AuditListItem[];
}

export interface ScoreCard {
  id: "lead_gen" | "seo" | "uxui";
  label: string;
  score: number;
  max_score: number;
  description: string;
}

export interface ReportFinding {
  section: string;
  severity: "info" | "low" | "medium" | "high";
  title: string;
  explanation: string;
  evidence_refs: string[];
  source: "commentary" | "rubric";
}

export interface ReportRecommendation {
  section: string;
  tier: "quick_win" | "mid_term" | "long_term";
  title: string;
  rationale: string;
  action_items: string[];
}

export interface ReportSection {
  id: string;
  label: string;
  headline: string;
  score: number | null;
  findings: ReportFinding[];
  recommendations: ReportRecommendation[];
}

export interface RoadmapTier {
  tier: string;
  label: string;
  recommendations: ReportRecommendation[];
}

export interface ValidationSummary {
  status: string;
  numeric_claims_checked: number;
  unsupported_claim_count: number;
  action: string;
}

export interface PageSpeedSummary {
  status: string;
  reason: string | null;
  scope: string | null;
  pages_requested: number;
  pages_analyzed: number;
  avg_mobile_performance: number | null;
  avg_desktop_performance: number | null;
}

export interface ReportMetadata {
  site_domain: string;
  niche: string | null;
  target_audience: string | null;
  generated_date: string;
  pages_crawled: number;
  failed_pages: number;
  rubric_version: string;
  llm_model: string;
}

export interface ReportPayload {
  version: string;
  metadata: ReportMetadata;
  scores: ScoreCard[];
  executive_summary: string;
  sections: ReportSection[];
  roadmap: RoadmapTier[];
  validation_summary: ValidationSummary;
  pagespeed_summary: PageSpeedSummary;
}

export interface AuditDetail {
  job_id: string;
  url: string;
  niche: string | null;
  target_audience: string | null;
  status: string;
  current_stage: string | null;
  progress_pct: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  report_available: boolean;
  report: ReportPayload | null;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && typeof detail.message === "string") {
      return detail.message;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      // FastAPI request-validation errors arrive as a list of issues.
      const first = detail[0];
      if (first?.msg) return String(first.msg);
    }
  } catch {
    // fall through to the generic message below
  }
  return `Request failed with status ${response.status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      `Could not reach the audit API. Make sure the backend is running on ${API_BASE_URL}.`,
      0,
    );
  }
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  return (await response.json()) as T;
}

export function createAudit(payload: AuditCreateRequest): Promise<AuditCreateResponse> {
  return request<AuditCreateResponse>("/audits", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listAudits(limit = 25): Promise<AuditListResponse> {
  return request<AuditListResponse>(`/audits?limit=${limit}`);
}

export function getAuditDetail(jobId: string): Promise<AuditDetail> {
  return request<AuditDetail>(`/audits/${jobId}`);
}

export function reportUrl(jobId: string): string {
  return `${API_BASE_URL}/audits/${jobId}/report`;
}
