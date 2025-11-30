import type { Feature, Geometry } from "geojson";

export interface FieldSummary {
  field_id: string;
  field_health_score: number;
  stress_label: string;
  overlay_path: string;
  svd_stats_path: string;
}

export interface NdviProfile {
  field_id: string;
  index: string;
  temporal_profile: number[];
  latest: number;
}

export interface SvdStats {
  field_id?: string;
  singular_values: number[];
  explained_variance: number[];
}

export interface DashboardState {
  summary?: FieldSummary;
  ndvi?: NdviProfile;
  svd?: SvdStats;
  overlayUrl?: string;
}

export type StressLevel = "low" | "moderate" | "high" | string;

export interface AvailableDatesResponse {
  field_id: string;
  dates: string[];
  source?: string;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface AnalysisJobRequest {
  field_id: string;
  start_date: string;
  end_date: string;
  geometry: Geometry;
  zip_code?: string;
  source?: string;
  properties?: FieldFeatureProperties;
}

export interface AnalysisJobRecord {
  job_id: string;
  field_id: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  start_date: string;
  end_date: string;
  zip_code: string;
  message?: string | null;
  result?: unknown;
}

export interface FieldAnalysisResponse {
  field_id: string;
  date: string;
  severity: StressLevel;
  confidence: number;
  trend: string;
  summary: string;
  recommendation?: string;
  overlays?: {
    cnn?: string;
    svd?: string;
  };
  metrics?: {
    ndvi?: number;
    recon_error?: number;
  };
}

export interface FieldFeatureProperties {
  field_id: string;
  name?: string;
  crop?: string;
  area_acres?: number;
  zip?: string;
}
