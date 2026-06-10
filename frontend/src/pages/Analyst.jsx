// Дашборд аналитика (Этап 2, шаг 11) — главный экран питча: карточки,
// карта узлов, динамика 90 дней, разбивки, прогноз, AI-сводка.
import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import AiSummary from "../components/analyst/AiSummary";
import Breakdowns from "../components/analyst/Breakdowns";
import CheckpointMap from "../components/analyst/CheckpointMap";
import EventFeed from "../components/analyst/EventFeed";
import Forecast from "../components/analyst/Forecast";
import TrafficChart from "../components/analyst/TrafficChart";
import { api } from "../api";

function StatCard({ label, value, unit }) {
  return (
    <div className="panel stat">
      <span className="stat-value">
        {value}
        {unit && <small> {unit}</small>}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

export default function Analyst() {
  const [overview, setOverview] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api("/analytics/overview"), api("/checkpoints")])
      .then(([ov, cps]) => {
        setOverview(ov);
        setCheckpoints(cps);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <Layout>
      {error && <div className="error">{error}</div>}

      {overview && (
        <div className="stats-row">
          <StatCard
            label="Машин за сутки"
            value={overview.trucks_today.toLocaleString("ru-RU")}
          />
          <StatCard
            label="Тонн в день (заявки, ср. за 7 дн.)"
            value={overview.tons_per_day.toLocaleString("ru-RU")}
            unit="т"
          />
          <StatCard label="Активных заявок" value={overview.active_requests} />
          <StatCard
            label="Средняя загрузка узлов"
            value={overview.avg_load_pct}
            unit="%"
          />
        </div>
      )}

      <div className="grid-map">
        <div className="panel map-panel">
          <h3>Узлы региона — текущая загрузка</h3>
          {checkpoints.length > 0 && <CheckpointMap checkpoints={checkpoints} />}
          <div className="legend">
            <span><i style={{ background: "#3fb68b" }} /> до 50%</span>
            <span><i style={{ background: "#f5a623" }} /> 50–85%</span>
            <span><i style={{ background: "#e2574c" }} /> от 85%</span>
          </div>
        </div>
        <div className="rail">
          <AiSummary />
          <EventFeed />
        </div>
      </div>

      <TrafficChart checkpoints={checkpoints} />
      <Breakdowns />
      <Forecast checkpoints={checkpoints} />
    </Layout>
  );
}
