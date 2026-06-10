// Разбивки потока за 90 дней: тип груза и направление (пироги) + узлы (бар).
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../../api";
import { TOOLTIP_STYLE } from "./TrafficChart";

const COLORS = ["#f5a623", "#3fb68b", "#6aa6ff", "#e2574c", "#8a94a6"];

function PiePanel({ title, items }) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie
            data={items}
            dataKey="trucks"
            nameKey="label"
            innerRadius={42}
            outerRadius={70}
            paddingAngle={2}
            stroke="none"
          >
            {items.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => `${v.toLocaleString("ru-RU")} машин`} />
        </PieChart>
      </ResponsiveContainer>
      <div className="legend">
        {items.map((it, i) => (
          <span key={it.key}>
            <i style={{ background: COLORS[i % COLORS.length] }} />
            {it.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Breakdowns() {
  const [cargo, setCargo] = useState([]);
  const [direction, setDirection] = useState([]);
  const [byCheckpoint, setByCheckpoint] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api("/analytics/breakdown?by=cargo_type"),
      api("/analytics/breakdown?by=direction"),
      api("/analytics/breakdown?by=checkpoint"),
    ])
      .then(([c, d, cp]) => {
        setCargo(c);
        setDirection(d);
        setByCheckpoint(cp);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <div className="grid-3">
      <PiePanel title="По типу груза" items={cargo} />
      <PiePanel title="По направлению" items={direction} />
      <div className="panel">
        <h3>По узлам</h3>
        <ResponsiveContainer width="100%" height={180 + 38}>
          <BarChart data={byCheckpoint} layout="vertical" margin={{ left: 8, right: 12 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="label"
              width={92}
              stroke="#8a94a6"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(v) => [`${v.toLocaleString("ru-RU")} машин`, "За 90 дней"]}
            />
            <Bar dataKey="trucks" fill="#6aa6ff" radius={[0, 4, 4, 0]} barSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
