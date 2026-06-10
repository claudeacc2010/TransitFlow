// Лента событий платформы: поллинг каждые 5 сек (websocket по спеке не нужен).
// Цвет точки — по типу события, время — относительное для «живого» ощущения.
import { useEffect, useState } from "react";
import { api } from "../../api";

const KIND_CLASS = {
  request: "ev-request",
  accept: "ev-accept",
  booking: "ev-booking",
};

const POLL_MS = 5000;

function timeAgo(iso) {
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return "только что";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} мин назад`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} ч назад`;
  return `${Math.floor(hr / 24)} дн назад`;
}

export default function EventFeed() {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    const load = () =>
      api("/events?limit=30")
        .then((data) => alive && setEvents(data))
        .catch((e) => alive && setError(e.message));

    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="panel">
      <div className="panel-title">
        <h3>Лента событий</h3>
        <span className="live-dot">live</span>
      </div>
      {error && <div className="error">{error}</div>}
      {events.length === 0 && !error ? (
        <p className="empty">Событий пока нет.</p>
      ) : (
        <div className="feed">
          {events.map((ev, i) => (
            <div className="feed-item" key={`${ev.ts}-${i}`}>
              <span className={`feed-dot ${KIND_CLASS[ev.kind] || ""}`} />
              <div className="feed-body">
                <div className="feed-head">
                  <b>{ev.title}</b>
                  <span className="feed-time">{timeAgo(ev.ts)}</span>
                </div>
                <div className="feed-detail">{ev.detail}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
