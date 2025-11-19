import type { NdviProfile } from "../types";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  profile: NdviProfile;
}

export function NdviChart({ profile }: Props) {
  const data = profile.temporal_profile.map((value, index) => ({
    label: `T${index + 1}`,
    value,
  }));

  return (
    <section className="card">
      <h2>NDVI trend</h2>
      <div className="chart-container">
        <ResponsiveContainer>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="label" stroke="#cbd5f5" tickLine={false} />
            <YAxis domain={[0, 1]} stroke="#cbd5f5" tickLine={false} />
            <Tooltip
              labelStyle={{ color: "#0f172a" }}
              contentStyle={{ borderRadius: "0.5rem" }}
              formatter={(value: number) => value.toFixed(2)}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#38bdf8"
              strokeWidth={3}
              dot={{ r: 4, fill: "#0f172a" }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p style={{ color: "#94a3b8" }}>
        Latest NDVI: <strong>{profile.latest.toFixed(2)}</strong>
      </p>
    </section>
  );
}
