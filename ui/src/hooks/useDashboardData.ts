import { useCallback, useState } from "react";
import {
  fetchFieldSummary,
  fetchNdviProfile,
  fetchSvdStats,
  getOverlayUrl,
} from "../lib/api";
import type { DashboardState } from "../types";

export function useDashboardData() {
  const [state, setState] = useState<DashboardState>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadField = useCallback(async (fieldId: string) => {
    setLoading(true);
    setError(null);
    try {
      const [summary, ndvi, svd] = await Promise.all([
        fetchFieldSummary(fieldId),
        fetchNdviProfile(fieldId),
        fetchSvdStats(fieldId),
      ]);
      setState({
        summary,
        ndvi,
        svd,
        overlayUrl: getOverlayUrl(fieldId),
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load field data";
      setError(message);
      setState({});
    } finally {
      setLoading(false);
    }
  }, []);

  return { state, loading, error, loadField };
}
