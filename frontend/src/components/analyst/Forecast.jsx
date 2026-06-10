// Прогноз на 7 дней по выбранному узлу. Бэкенд отдаёт 168 часовых точек
// (бейзлайн день-недели × час + тренд) — для читаемости агрегируем в сутки,
// пиковый час показываем подписью под графиком.
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../../api";
import { TOOLTIP_STYLE } from "./TrafficChart";

const DAY_RU = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];

const fmtDay = (iso) => {
  const d = new Date(iso);
  return `${DAY_RU[d.getUTCDay()]} ${String(d.getUTCDate()).padStart(2, "0")}.${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
};

export default function Forecast({ checkpoints }) {
  const [checkpointId, setCheckpointId] = useState(null);
  const [points, setPoints] = useState([]);
  const [error, setError] = useState("");

  // По умолчанию — самый загруженный узел: про него аналитику интереснее всего.
  useEffect(() => {
    if (checkpointId === null && checkpoints.length) {
      const busiest = [...checkpoints].sort((a, b) => b.load_pct - a.load_pct)[0];
      setCheckpointId(busiest.id);
    }
  }, [checkpoints, checkpointId]);

  useEffect(() => {
    if (checkpointId === null) return;
    api(`/checkpoints/${checkpointId}/forecast?days=7`)
      .then((fc) => setPoints(fc.points))
      .catch((e) => setError(e.message));
  }, [checkpointId]);

  const { daily, peak } = useMemo(() => {
    const byDay = new Map();
    let peakPoint = null;
    for (const p of points) {
      const day = p.ts.slice(0, 10);
      byDay.set(day, (byDay.get(day) || 0) + p.trucks_expected);
      if (!peakPoint || p.trucks_expected > peakPoint.trucks_expected) peakPoint = p;
    }
    return {
      daily: [...byDay.entries()].map(([day, trucks]) => ({
        day,
        trucks: Math.round(trucks),
      })),
      peak: peakPoint,
    };
  }, [points]);

  return (
    <div className="panel">
      <div className="panel-title">
        <h3>Прогноз на 7 дней</h3>
        <select
          className="select-inline"
          value={checkpointId ?? ""}
          onChange={(e) => setCheckpointId(Number(e.target.value))}
        >
          {checkpoints.map((cp) => (
            <option key={cp.id} value={cp.id}>
              {cp.name}
            </option>
          ))}
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={daily} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid stroke="#2a323f" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" tickFormatter={fmtDay} stroke="#5d6675" fontSize={11} />
          <YAxis stroke="#5d6675" fontSize={11} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelFormatter={fmtDay}
            formatter={(v) => [`~${v.toLocaleString("ru-RU")} машин`, "Ожидается"]}
          />
          <Bar dataKey="trucks" fill="#3fb68b" radius={[4, 4, 0, 0]} barSize={32} />
        </BarChart>
      </ResponsiveContainer>
      <p className="forecast-note">
        {peak &&
          `Пиковый час: ${fmtDay(peak.ts)}, ${peak.ts.slice(11, 16)} UTC — ~${Math.round(peak.trucks_expected)} маш/ч. `}
        Бейзлайн-модель (день недели × час, тренд 14 дней) — заменяется на ML при подключении реальных данных.
      </p>
    </div>
  );
}
