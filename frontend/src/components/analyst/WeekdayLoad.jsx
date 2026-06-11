// §7: пик нагрузки по дням недели — 7 столбцов из /analytics/weekday-load.
// Пиковый день подсвечен — акимат видит, когда усиливать смены на узлах.
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
import { api } from "../../api";
import { TOOLTIP_STYLE } from "./TrafficChart";

export default function WeekdayLoad() {
  const [data, setData] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/analytics/weekday-load")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  const peak = data.reduce((m, d) => (d.trucks > m ? d.trucks : m), 0);

  return (
    <div className="panel">
      <h3>Пик нагрузки по дням недели</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 8, left: 8, right: 8 }}>
          <XAxis
            dataKey="label"
            stroke="#8a94a6"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: "#ffffff0a" }}
            formatter={(v) => [`${v.toLocaleString("ru-RU")} машин`, "За 90 дней"]}
          />
          <Bar dataKey="trucks" radius={[4, 4, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.dow} fill={d.trucks === peak ? "#f5a623" : "#6aa6ff"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
