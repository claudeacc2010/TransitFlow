// §7: узкие места — топ-3 узла по ожиданию в очереди (из §5, данные узлов).
// Без отдельного запроса: переиспуем checkpoints, уже загруженные дашбордом.

function waitClass(h) {
  if (h >= 8) return "bn-bad";
  if (h >= 3) return "bn-warn";
  return "bn-ok";
}

export default function Bottlenecks({ checkpoints }) {
  const top = [...checkpoints]
    .sort((a, b) => b.est_wait_hours - a.est_wait_hours)
    .slice(0, 3);

  return (
    <div className="panel">
      <h3>Узкие места</h3>
      <div className="bottlenecks">
        {top.map((cp, i) => (
          <div key={cp.id} className="bn-row">
            <span className="bn-rank">{i + 1}</span>
            <div className="bn-body">
              <div className="bn-name">{cp.name}</div>
              <div className="bn-meta">
                ожидают {cp.waiting_now} · {cp.capacity_per_day}/сутки
              </div>
            </div>
            <span className={`bn-wait ${waitClass(cp.est_wait_hours)}`}>
              {cp.est_wait_hours > 0 ? `≈ ${cp.est_wait_hours} ч` : "свободно"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
