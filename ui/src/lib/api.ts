import axios from "axios";
import type { FieldSummary, NdviProfile, SvdStats } from "../types";

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
