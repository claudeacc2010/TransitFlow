// Дашборд аналитика (Этап 2, шаг 11) — главный экран питча: карточки,
// карта узлов, динамика 90 дней, разбивки, прогноз, AI-сводка.
import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import AiSummary from "../components/analyst/AiSummary";
import Bottlenecks from "../components/analyst/Bottlenecks";
import Breakdowns from "../components/analyst/Breakdowns";
import CheckpointMap from "../components/analyst/CheckpointMap";
import EventFeed from "../components/analyst/EventFeed";
import Forecast from "../components/analyst/Forecast";
import TrafficChart from "../components/analyst/TrafficChart";
import WeekdayLoad from "../components/analyst/WeekdayLoad";
import { api, downloadFile } from "../api";

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
  const [pdfBusy, setPdfBusy] = useState(false);

  useEffect(() => {
    Promise.all([api("/analytics/overview"), api("/checkpoints")])
      .then(([ov, cps]) => {
        setOverview(ov);
        setCheckpoints(cps);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function downloadReport() {
    setError("");
    setPdfBusy(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      await downloadFile("/analytics/report.pdf", `transitflow_report_${today}.pdf`);
    } catch (e) {
      setError(e.message || "Не удалось сформировать отчёт");
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <Layout>
      <div className="analyst-head">
        <h2>Дашборд акимата</h2>
        <button className="btn-primary btn-sm" onClick={downloadReport} disabled={pdfBusy}>
          {pdfBusy ? "Готовим отчёт…" : "📄 Скачать PDF-отчёт"}
        </button>
      </div>

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
          <h3>Узлы региона — ожидание в очереди</h3>
          {checkpoints.length > 0 && <CheckpointMap checkpoints={checkpoints} />}
          <div className="legend">
            <span><i style={{ background: "#3fb68b" }} /> свободно (&lt; 3 ч)</span>
            <span><i style={{ background: "#f5a623" }} /> напряжённо (3–8 ч)</span>
            <span><i style={{ background: "#e2574c" }} /> затор (8+ ч)</span>
            <span className="legend-note">стрелки — транзитные коридоры</span>
          </div>
        </div>
        <div className="rail">
          <AiSummary />
          <EventFeed />
        </div>
      </div>

      <TrafficChart checkpoints={checkpoints} />
      <Breakdowns />
      <div className="grid-2">
        {checkpoints.length > 0 && <Bottlenecks checkpoints={checkpoints} />}
        <WeekdayLoad />
      </div>
      <Forecast checkpoints={checkpoints} />
    </Layout>
  );
}
