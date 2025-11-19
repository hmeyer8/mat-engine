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
