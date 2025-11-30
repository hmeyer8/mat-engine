import axios from "axios";
import type { FeatureCollection } from "geojson";
import type {
  AvailableDatesResponse,
  AnalysisJobRecord,
  AnalysisJobRequest,
  FieldAnalysisResponse,
  FieldSummary,
  NdviProfile,
  SvdStats,
} from "../types";

const baseURL =
  import.meta.env.VITE_NEXT_PUBLIC_API_URL ||
  import.meta.env.VITE_API_URL ||
  import.meta.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8080";

export const api = axios.create({
  baseURL,
  timeout: 15_000,
});

export async function fetchFieldSummary(fieldId: string) {
  const { data } = await api.get<FieldSummary>(`/fields/${fieldId}/summary`);
  return data;
}

export async function fetchNdviProfile(fieldId: string) {
  const { data } = await api.get<NdviProfile>(
    `/fields/${fieldId}/indices/ndvi`
  );
  return data;
}

export async function fetchSvdStats(fieldId: string) {
  const { data } = await api.get<SvdStats>(`/fields/${fieldId}/svd/stats`);
  return data;
}

export function getOverlayUrl(fieldId: string) {
  const timestamp = Date.now();
  return `${baseURL}/fields/${fieldId}/overlay?ts=${timestamp}`;
}

export function getApiBaseUrl() {
  return baseURL;
}

export async function fetchAvailableDates(fieldId: string) {
  try {
    const { data } = await api.get<AvailableDatesResponse>(
      `/api/available_dates`,
      {
        params: { field_id: fieldId },
      }
    );
    return data;
  } catch (error) {
    console.warn("Falling back to placeholder dates", error);
    return {
      field_id: fieldId,
      dates: buildFallbackDates(),
      source: "placeholder",
    } satisfies AvailableDatesResponse;
  }
}

function buildFallbackDates() {
  const today = new Date();
  const dates: string[] = [];
  for (let i = 0; i < 6; i += 1) {
    const clone = new Date(today);
    clone.setDate(today.getDate() - i * 7);
    dates.push(clone.toISOString().slice(0, 10));
  }
  return dates;
}

export async function fetchOsmFields(
  bbox: string,
  crop?: string
): Promise<FeatureCollection> {
  const params: Record<string, string> = { bbox };
  if (crop) {
    params.crop = crop;
  }
  const { data } = await api.get<FeatureCollection>("/api/fields/osm", {
    params,
  });
  return data;
}

export async function startAnalysisJob(payload: AnalysisJobRequest) {
  const { data } = await api.post<AnalysisJobRecord>(`/api/jobs`, payload);
  return data;
}

export async function getJobStatus(jobId: string) {
  const { data } = await api.get<AnalysisJobRecord>(`/api/jobs/${jobId}`);
  return data;
}

export async function fetchAnalysisSnapshot(fieldId: string) {
  const { data } = await api.get<FieldAnalysisResponse>(
    `/api/analysis/${fieldId}`
  );
  return data;
}
