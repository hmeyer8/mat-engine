import type { SvdStats } from "../types";

interface Props {
  stats: SvdStats;
}

export function SvdPanel({ stats }: Props) {
  return (
    <section className="card">
      <h2>Temporal SVD</h2>
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div>
          <h3>Singular values</h3>
          <ol>
            {stats.singular_values.map((value, index) => (
              <li key={`sv-${index}`}>{value.toFixed(4)}</li>
            ))}
          </ol>
        </div>
        <div>
          <h3>Explained variance</h3>
          <ol>
            {stats.explained_variance.map((value, index) => (
              <li key={`var-${index}`}>{(value * 100).toFixed(2)}%</li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
