// Кабинет отправителя: создать заявку + список своих заявок со статусами.
import { useEffect, useState } from "react";

import { api } from "../api";
import Layout from "../components/Layout";
import {
  CARGO_OPTIONS,
  CARGO_RU,
  SHIPMENT_STEPS,
  STATUS_RU,
  fmtDate,
  fmtMoney,
  fmtSlot,
  shipmentStepIndex,
} from "../labels";

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
  price_offer: "",
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
    price_offer: form.price_offer === "" ? null : Number(form.price_offer),
  };
}

export default function Shipper() {
  const [form, setForm] = useState(EMPTY);
  const [requests, setRequests] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [rec, setRec] = useState(null); // рекомендованная цена (§2)
  const [recBusy, setRecBusy] = useState(false);

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

  // §2: запросить рекомендованную цену по текущим параметрам.
  async function getRecommendation() {
    if (!form.origin || !form.destination || !form.weight_t) {
      setError("Для расчёта цены укажите маршрут и вес");
      return;
    }
    setError("");
    setRecBusy(true);
    try {
      const r = await api("/requests/recommend-price", {
        method: "POST",
        body: {
          cargo_type: form.cargo_type,
          weight_t: Number(form.weight_t),
          origin: form.origin,
          destination: form.destination,
          adr_class: form.adr_on ? form.adr_class : null,
          temp_mode: form.temp_mode.trim() || null,
          urgency: form.urgency,
        },
      });
      setRec(r);
    } catch (err) {
      setError(err.message);
    } finally {
      setRecBusy(false);
    }
  }

  // Предупреждение, если своя цена занижена относительно рекомендованной >20%.
  const priceLow =
    rec && form.price_offer !== "" && Number(form.price_offer) < rec.recommended * 0.8;

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
      setRec(null);
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

            {/* §2: рекомендованная цена + своя цена */}
            <div className="price-box">
              <button
                type="button"
                className="btn-ghost btn-block"
                onClick={getRecommendation}
                disabled={recBusy}
              >
                {recBusy ? "Считаем…" : "Рассчитать рекомендованную цену"}
              </button>
              {rec && (
                <div className="rec-price">
                  <div className="rec-head">
                    Рекомендуем <b>{fmtMoney(rec.recommended)}</b>
                    <span className="rec-sub">
                      {rec.distance_km} км · {rec.rate_per_km_t} ₸/км·т
                    </span>
                  </div>
                  {rec.factors.length > 0 && (
                    <div className="rec-factors">
                      {rec.factors.map((f) => (
                        <span key={f.label} className="chip chip-adr">
                          {f.label} ×{f.multiplier}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <label>Ваша цена за перевозку, ₸</label>
              <input
                type="number"
                min="1"
                step="1000"
                value={form.price_offer}
                onChange={(e) => set("price_offer", e.target.value)}
                placeholder={rec ? String(rec.recommended) : "напр. 380000"}
              />
              {priceLow && (
                <div className="warn">
                  Цена ниже рекомендованной на 20%+ — перевозчики могут не взять заказ.
                </div>
              )}
            </div>

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

// §3: горизонтальный степпер жизненного цикла груза.
function Stepper({ current }) {
  return (
    <div className="stepper">
      {SHIPMENT_STEPS.map((label, i) => {
        const state = i < current ? "done" : i === current ? "active" : "todo";
        return (
          <div key={label} className={`step step-${state}`}>
            <span className="step-dot" />
            <span className="step-label">{label}</span>
          </div>
        );
      })}
    </div>
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
        {r.price_offer && (
          <span>
            цена: <b>{fmtMoney(r.price_offer)}</b>
            {r.price_per_km ? <> · {r.price_per_km} ₸/км</> : null}
          </span>
        )}
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
      {r.status !== "cancelled" && <Stepper current={shipmentStepIndex(r)} />}
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
