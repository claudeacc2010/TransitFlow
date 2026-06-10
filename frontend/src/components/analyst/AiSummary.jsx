// AI-сводка: по кнопке собирается статистика из БД и уходит провайдеру
// (Gemini/Claude — настройка бэкенда). Бейдж показывает источник ответа:
// живой API, кеш последней удачной сводки или детерминированный fallback.
import { useState } from "react";
import { api } from "../../api";

const SOURCE_RU = {
  gemini: ["Gemini", "badge-slot_booked"],
  claude: ["Claude", "badge-slot_booked"],
  cache: ["из кеша", "badge-open"],
  fallback: ["без AI", "badge-cancelled"],
};

export default function AiSummary() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    setLoading(true);
    setError("");
    try {
      setSummary(await api("/analytics/ai-summary", { method: "POST" }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const [sourceLabel, sourceClass] = summary
    ? SOURCE_RU[summary.provider] || [summary.provider, "badge-open"]
    : [];

  return (
    <div className="panel">
      <div className="panel-title">
        <h3>AI-сводка</h3>
        {summary && <span className={`badge ${sourceClass}`}>{sourceLabel}</span>}
      </div>
      {error && <div className="error">{error}</div>}
      {summary ? (
        <p className="ai-text">{summary.summary}</p>
      ) : (
        <p className="empty">
          Краткий разбор ситуации на узлах по текущим данным платформы.
        </p>
      )}
      <button className="btn-primary btn-block" onClick={generate} disabled={loading}>
        {loading ? "Анализирую…" : summary ? "Обновить сводку" : "Сформировать сводку"}
      </button>
    </div>
  );
}
