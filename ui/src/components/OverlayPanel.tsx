interface Props {
  overlayUrl?: string;
  fieldId: string;
}

const legendEntries = [
  { label: "Healthy", color: "#22c55e" },
  { label: "Emerging stress", color: "#eab308" },
  { label: "Moderate", color: "#f97316" },
  { label: "Severe", color: "#ef4444" },
];

export function OverlayPanel({ overlayUrl, fieldId }: Props) {
  return (
    <section className="card">
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h2 style={{ marginBottom: "0.75rem" }}>Stress overlay</h2>
        {overlayUrl && (
          <a href={overlayUrl} download={`${fieldId}-overlay.png`}>
            Download PNG
          </a>
        )}
      </div>
      {overlayUrl ? (
        <img
          src={overlayUrl}
          alt={`Stress overlay for ${fieldId}`}
          className="overlay-image"
        />
      ) : (
        <p>No overlay available. Run the pipeline first.</p>
      )}
      <div className="legend">
        {legendEntries.map((entry) => (
          <span key={entry.label} className="legend-item">
            <span
              className="legend-swatch"
              style={{ background: entry.color }}
            />
            {entry.label}
          </span>
        ))}
      </div>
    </section>
  );
}
