import type { FieldSummary } from "../types";

const stressColors: Record<string, string> = {
  low: "#22c55e",
  moderate: "#eab308",
  high: "#f97316",
  severe: "#ef4444",
};

interface Props {
  summary: FieldSummary;
}

export function SummaryCard({ summary }: Props) {
  const color = stressColors[summary.stress_label.toLowerCase()] || "#38bdf8";
  return (
    <section className="card">
      <h2>Field summary</h2>
      <p>Field ID: {summary.field_id}</p>
      <p>
        Health score: <strong>{(summary.field_health_score * 100).toFixed(1)}%</strong>
      </p>
      <div
        className="status-pill"
        style={{ background: `${color}33`, color }}
      >
        <span
          className="legend-swatch"
          style={{ background: color, borderRadius: "50%" }}
        />
        {summary.stress_label}
      </div>
      <small style={{ display: "block", marginTop: "1rem", color: "#94a3b8" }}>
        Overlay path: {summary.overlay_path}
      </small>
    </section>
  );
}
