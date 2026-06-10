// Динамика потока: машин/сутки за 90 дней, все узлы или один (селектор).
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../../api";

const fmtDay = (iso) => {
  const d = new Date(iso);
  return `${String(d.getUTCDate()).padStart(2, "0")}.${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
};

export const TOOLTIP_STYLE = {
  backgroundColor: "#1c222b",
  border: "1px solid #2a323f",
  borderRadius: 8,
  color: "#e8ecf1",
  fontSize: 13,
};

export default function TrafficChart({ checkpoints }) {
  const [checkpointId, setCheckpointId] = useState("");
  const [points, setPoints] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const qs = checkpointId ? `&checkpoint_id=${checkpointId}` : "";
    api(`/analytics/timeseries?days=90${qs}`)
      .then(setPoints)
      .catch((e) => setError(e.message));
  }, [checkpointId]);

  return (
    <div className="panel">
      <div className="panel-title">
        <h3>Динамика за 90 дней</h3>
        <select
          className="select-inline"
          value={checkpointId}
          onChange={(e) => setCheckpointId(e.target.value)}
        >
          <option value="">Все узлы</option>
          {checkpoints.map((cp) => (
            <option key={cp.id} value={cp.id}>
              {cp.name}
            </option>
          ))}
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={points} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="traffic" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f5a623" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#f5a623" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#2a323f" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={fmtDay}
            stroke="#5d6675"
            fontSize={11}
            minTickGap={36}
          />
          <YAxis stroke="#5d6675" fontSize={11} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelFormatter={fmtDay}
            formatter={(v) => [`${v} машин`, "За сутки"]}
          />
          <Area
            type="monotone"
            dataKey="trucks"
            stroke="#f5a623"
            strokeWidth={2}
            fill="url(#traffic)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
