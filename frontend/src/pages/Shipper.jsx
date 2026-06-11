// Кабинет отправителя: создать заявку + список своих заявок со статусами.
import { useEffect, useState } from "react";

import { api } from "../api";
import Layout from "../components/Layout";
import { CARGO_OPTIONS, CARGO_RU, STATUS_RU, fmtDate, fmtSlot } from "../labels";

const todayISO = () => new Date().toISOString().slice(0, 10);

const EMPTY = {
  cargo_type: "container",
  weight_t: "",
  volume_m3: "",
  origin: "",
  destination: "",
  desired_date: todayISO(),
  adr_on: false,
  adr_class: "3",
  temp_mode: "",
  urgency: "normal",
};

const ADR_CLASSES = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

// Форма → тело запроса: пустые опции превращаем в null, числа парсим.
function buildPayload(form) {
  return {
    cargo_type: form.cargo_type,
    weight_t: Number(form.weight_t),
    volume_m3: form.volume_m3 === "" ? null : Number(form.volume_m3),
    origin: form.origin,
    destination: form.destination,
    desired_date: form.desired_date,
    adr_class: form.adr_on ? form.adr_class : null,
    temp_mode: form.temp_mode.trim() === "" ? null : form.temp_mode.trim(),
    urgency: form.urgency,
  };
}

export default function Shipper() {
  const [form, setForm] = useState(EMPTY);
  const [requests, setRequests] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setRequests(await api("/requests?mine=1"));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/requests", {
        method: "POST",
        body: buildPayload(form),
      });
      setForm({ ...EMPTY, desired_date: todayISO() });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout>
      <div className="grid-2">
        {/* --- Форма заявки --- */}
        <div className="panel">
          <h2>Новая заявка</h2>
          <form onSubmit={submit}>
            <label>Тип груза</label>
            <select value={form.cargo_type} onChange={(e) => set("cargo_type", e.target.value)}>
              {CARGO_OPTIONS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>

            <div className="row-2">
              <div>
                <label>Вес, т</label>
                <input
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={form.weight_t}
                  onChange={(e) => set("weight_t", e.target.value)}
                  placeholder="18.5"
                  required
                />
              </div>
              <div>
                <label>Объём, м³</label>
                <input
                  type="number"
                  min="0.1"
                  max="200"
                  step="0.1"
                  value={form.volume_m3}
                  onChange={(e) => set("volume_m3", e.target.value)}
                  placeholder="36"
                />
              </div>
            </div>

            <div className="row-2">
              <div>
                <label>Откуда</label>
                <input
                  value={form.origin}
                  onChange={(e) => set("origin", e.target.value)}
                  placeholder="Актау"
                  required
                />
              </div>
              <div>
                <label>Куда</label>
                <input
                  value={form.destination}
                  onChange={(e) => set("destination", e.target.value)}
                  placeholder="Бейнеу"
                  required
                />
              </div>
            </div>

            <div className="row-2">
              <div>
                <label>Срочность</label>
                <select value={form.urgency} onChange={(e) => set("urgency", e.target.value)}>
                  <option value="normal">Обычная</option>
                  <option value="urgent">Срочно</option>
                </select>
              </div>
              <div>
                <label>Температурный режим</label>
                <input
                  value={form.temp_mode}
                  onChange={(e) => set("temp_mode", e.target.value)}
                  placeholder="напр. +2..+6 (пусто — обычный)"
                />
              </div>
            </div>

            <label className="check-row">
              <input
                type="checkbox"
                checked={form.adr_on}
                onChange={(e) => set("adr_on", e.target.checked)}
              />
              Опасный груз (ADR)
            </label>
            {form.adr_on && (
              <select value={form.adr_class} onChange={(e) => set("adr_class", e.target.value)}>
                {ADR_CLASSES.map((c) => (
                  <option key={c} value={c}>
                    Класс {c}
                  </option>
                ))}
              </select>
            )}

            <label>Желаемая дата</label>
            <input
              type="date"
              value={form.desired_date}
              onChange={(e) => set("desired_date", e.target.value)}
              required
            />

            <button className="btn-primary btn-block" disabled={busy} type="submit">
              Создать заявку
            </button>
          </form>
          {error && <div className="error">{error}</div>}
        </div>

        {/* --- Список своих заявок --- */}
        <div className="panel">
          <div className="panel-title">
            <h2>Мои заявки</h2>
            <span className="units">{requests.length} шт</span>
          </div>

          {requests.length === 0 ? (
            <div className="empty">Заявок пока нет — создайте первую слева.</div>
          ) : (
            <div className="list">
              {requests.map((r) => (
                <RequestRow key={r.id} r={r} />
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

function RequestRow({ r }) {
  const a = r.assignment;
  const b = a?.booking;
  return (
    <div className="item">
      <div className="item-head">
        <span className="item-route">
          {r.origin} → {r.destination}
        </span>
        <span className={`badge badge-${r.status}`}>{STATUS_RU[r.status]}</span>
      </div>
      <div className="item-meta">
        <span>
          {CARGO_RU[r.cargo_type]}, <b>{r.weight_t} т</b>
          {r.volume_m3 ? <> · {r.volume_m3} м³</> : null}
        </span>
        <span>
          на <b>{fmtDate(r.desired_date)}</b>
        </span>
      </div>
      {(r.urgency === "urgent" || r.adr_class || r.temp_mode) && (
        <div className="item-badges">
          {r.urgency === "urgent" && <span className="chip chip-urgent">Срочно</span>}
          {r.adr_class && <span className="chip chip-adr">ADR {r.adr_class}</span>}
          {r.temp_mode && <span className="chip chip-temp">❄ {r.temp_mode}</span>}
        </div>
      )}
      {a && (
        <div className="item-meta" style={{ marginTop: 6 }}>
          <span>
            перевозчик: <b>{a.carrier.company || a.carrier.name}</b> · {a.truck_plate}
          </span>
        </div>
      )}
      {b && (
        <div className="item-meta" style={{ marginTop: 6 }}>
          <span>
            слот: <b>{b.checkpoint_name}</b>, {fmtSlot(b)}
          </span>
          <a href={`/pass/${b.qr_token}`} target="_blank" rel="noreferrer">
            пропуск ↗
          </a>
        </div>
      )}
    </div>
  );
}
