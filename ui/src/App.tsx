import { useEffect, useMemo, useState } from "react";
import { FieldSelector } from "./components/FieldSelector";
import { SummaryCard } from "./components/SummaryCard";
import { OverlayPanel } from "./components/OverlayPanel";
import { NdviChart } from "./components/NdviChart";
import { SvdPanel } from "./components/SvdPanel";
import { useDashboardData } from "./hooks/useDashboardData";
import { getApiBaseUrl } from "./lib/api";

function App() {
  const defaultField = useMemo(() => "demo-field", []);
  const [fieldId, setFieldId] = useState(defaultField);
  const { state, loading, error, loadField } = useDashboardData();

  useEffect(() => {
    loadField(defaultField);
  }, [defaultField, loadField]);

  const handleSubmit = () => {
    if (fieldId.trim()) {
      loadField(fieldId.trim());
    }
  };

  return (
    <main>
      <h1>MAT Engine Farmer Dashboard</h1>
      <p style={{ color: "#94a3b8", marginBottom: "1.5rem" }}>
  Point the UI at <code>{getApiBaseUrl()}</code>, run the pipeline, and
  view overlays + NDVI trends instantly.
      </p>

      <FieldSelector
        fieldId={fieldId}
        onChange={setFieldId}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {error && (
        <section className="card" style={{ borderColor: "#ef4444" }}>
          <strong>Error:</strong> {error}
        </section>
      )}

      <section className="grid">
        {state.summary && <SummaryCard summary={state.summary} />}
        {state.ndvi && <NdviChart profile={state.ndvi} />}
        {state.overlayUrl && state.summary && (
          <OverlayPanel
            overlayUrl={state.overlayUrl}
            fieldId={state.summary.field_id}
          />
        )}
        {state.svd && <SvdPanel stats={state.svd} />}
      </section>

      <footer>
        Powered by MAT Engine · FastAPI backend · React/Vite UI
      </footer>
    </main>
  );
}

export default App;
