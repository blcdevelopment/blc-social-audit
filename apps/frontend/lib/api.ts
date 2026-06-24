// Typed client for the BLC Website Audit API.
// The base URL is configurable so the operator UI can point at a non-local API later.
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

export type ReportFormat = "pdf" | "docx";

interface ApiRequestInit extends RequestInit {
  authToken?: string | null;
}

export interface BrandOverrides {
  name?: string | null;
  short_name?: string | null;
  primary_color?: string | null;
  accent_color?: string | null;
  logo_url?: string | null;
}

export interface AuditCreateRequest {
  url?: string | null;
  audit_type?: "website" | "social";
  niche?: string | null;
  target_audience?: string | null;
  brand_overrides?: BrandOverrides | null;
  social_handles?: Record<string, string> | null;
}

export interface SocialReportFinding {
  id: string;
  label: string;
  remediation: string | null;
  impact: string;
  tier: string;
  result: string;
  narrative?: string;
}

export interface SocialReport {
  version: string;
  score: number | null;
  status: string;
  handles: Record<string, string>;
  generated_date: string;
  platforms_audited: number;
  summary: Record<string, unknown>;
  platforms: Record<string, unknown>[];
  executive_summary?: string;
  commentary_provider?: string;
  findings: SocialReportFinding[];
  roadmap: Record<string, SocialReportFinding[]>;
}

export interface AuditCreateResponse {
  job_id: string;
  status: string;
  status_url: string;
}

export interface AuditShareResponse {
  job_id: string;
  share_token: string;
  share_expires_at: string;
  report_path: string;
}

export interface AuditListItem {
  job_id: string;
  url: string;
  audit_type: string;
  status: string;
  current_stage: string | null;
  progress_pct: number;
  created_at: string;
  completed_at: string | null;
  seo_score: number | null;
  uxui_score: number | null;
  lead_gen_score: number | null;
  social_score: number | null;
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
  opportunities: RuleSummary[];
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

export interface ExternalSeoSummary {
  status: string;
  technical_crawl_status: string;
  technical_crawl_tool: string | null;
  gsc_status: string;
  url_inspection_status: string;
  technical_issue_count: number;
  search_opportunity_count: number;
}

export interface TechnicalSeoIssue {
  id: string;
  severity: "info" | "low" | "medium" | "high";
  title: string;
  count: number;
  summary: string;
  why_it_matters: string;
  recommended_fix: string;
  location_label: string;
  examples: string[];
}

export interface TechnicalSeoSection {
  status: string;
  status_label: string;
  reason_label: string | null;
  source: string | null;
  tool_label: string | null;
  summary: Record<string, unknown>;
  issues: TechnicalSeoIssue[];
  notes: string[];
  warnings: string[];
}

export interface SearchPerformanceSection {
  status: string;
  status_label: string;
  reason_label: string | null;
  site_url: string | null;
  date_range: Record<string, unknown>;
  summary: Record<string, unknown>;
  top_queries: Record<string, unknown>[];
  top_pages: Record<string, unknown>[];
  high_impression_low_ctr_pages: Record<string, unknown>[];
  ranking_opportunities: Record<string, unknown>[];
  declining_pages: Record<string, unknown>[];
  url_inspection_summary: Record<string, unknown>;
  url_inspection_items: Record<string, unknown>[];
}

export interface SearchConsoleProperty {
  siteUrl: string;
  permissionLevel?: string | null;
}

export interface SearchConsolePropertiesResponse {
  status: string;
  account_email: string | null;
  properties: SearchConsoleProperty[];
  reason: string | null;
}

export interface SearchConsoleConnectUrlResponse {
  status: string;
  connect_url: string | null;
  reason: string | null;
}

export interface RuleSummary {
  rule_id: string;
  description: string;
  result: "pass" | "partial" | "fail" | "skipped";
  points_awarded: number;
  points_possible: number;
  evidence_value: string | null;
  reason: string | null;
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
  external_seo_summary: ExternalSeoSummary;
  technical_seo_section: TechnicalSeoSection;
  search_performance_section: SearchPerformanceSection;
}

export interface AuditDetail {
  job_id: string;
  url: string;
  audit_type: string;
  niche: string | null;
  target_audience: string | null;
  social_handles?: Record<string, string> | null;
  status: string;
  current_stage: string | null;
  progress_pct: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  report_available: boolean;
  seo_score?: number | null;
  uxui_score?: number | null;
  lead_gen_score?: number | null;
  social_score?: number | null;
  report: ReportPayload | null;
  social_report?: SocialReport | null;
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

function requestHeaders(authToken?: string | null, includeJson = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeJson) headers["Content-Type"] = "application/json";
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  return headers;
}

async function request<T>(path: string, init?: ApiRequestInit): Promise<T> {
  const { authToken, headers, ...requestInit } = init || {};
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      headers: {
        ...requestHeaders(authToken),
        ...(headers as Record<string, string> | undefined),
      },
      ...requestInit,
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

export function createAudit(
  payload: AuditCreateRequest,
  authToken?: string | null,
): Promise<AuditCreateResponse> {
  return request<AuditCreateResponse>("/audits", {
    method: "POST",
    authToken,
    body: JSON.stringify(payload),
  });
}

export function listAudits(
  limit = 25,
  authToken?: string | null,
): Promise<AuditListResponse> {
  return request<AuditListResponse>(`/audits?limit=${limit}`, { authToken });
}

export function getAuditDetail(
  jobId: string,
  authToken?: string | null,
): Promise<AuditDetail> {
  return request<AuditDetail>(`/audits/${jobId}`, { authToken });
}

export function reportUrl(jobId: string, format: ReportFormat = "pdf"): string {
  return `${API_BASE_URL}/audits/${jobId}/${format === "pdf" ? "report" : "docx"}`;
}

export function getSearchConsoleProperties(
  authToken?: string | null,
): Promise<SearchConsolePropertiesResponse> {
  return request<SearchConsolePropertiesResponse>("/google/search-console/properties", {
    authToken,
  });
}

export function createSearchConsoleConnectUrl(
  authToken?: string | null,
): Promise<SearchConsoleConnectUrlResponse> {
  return request<SearchConsoleConnectUrlResponse>("/google/search-console/connect-url", {
    authToken,
  });
}

export function rerunAuditEnrichment(
  jobId: string,
  authToken?: string | null,
): Promise<{ job_id: string; status: string; current_stage: string | null; message: string }> {
  return request(`/audits/${jobId}/rerun-enrichment`, {
    method: "POST",
    authToken,
  });
}

export function shareAudit(
  jobId: string,
  authToken?: string | null,
): Promise<AuditShareResponse> {
  return request<AuditShareResponse>(`/audits/${jobId}/share`, {
    method: "POST",
    authToken,
  });
}

export function revokeShare(
  jobId: string,
  authToken?: string | null,
): Promise<{ job_id: string; shared: boolean }> {
  return request(`/audits/${jobId}/share`, {
    method: "DELETE",
    authToken,
  });
}

// Builds the absolute, login-free report URL from the API's relative report_path.
export function shareUrlFromPath(reportPath: string): string {
  return `${API_BASE_URL}${reportPath}`;
}

function filenameFromDisposition(disposition: string | null, fallback: string): string {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

export async function downloadReport(
  jobId: string,
  format: ReportFormat,
  authToken?: string | null,
): Promise<{ blob: Blob; filename: string }> {
  let response: Response;
  try {
    response = await fetch(reportUrl(jobId, format), {
      credentials: "include",
      headers: requestHeaders(authToken, false),
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
  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(
      response.headers.get("content-disposition"),
      `blc-website-audit-${jobId}.${format}`,
    ),
  };
}
