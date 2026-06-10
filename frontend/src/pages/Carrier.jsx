// Кабинет перевозчика: лента открытых заявок → принять → выбрать слот → QR.
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import { api } from "../api";
import Layout from "../components/Layout";
import { CARGO_RU, STATUS_RU, fmtDate, fmtSlot } from "../labels";

export default function Carrier() {
  const [open, setOpen] = useState([]);
  const [mine, setMine] = useState([]);
  const [checkpoints, setCheckpoints] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [o, m, cp] = await Promise.all([
        api("/requests?status=open"),
        api("/requests?mine=1"),
        api("/checkpoints"),
      ]);
      setOpen(o);
      setMine(m);
      setCheckpoints(cp);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  // «Активные» у перевозчика — принятые и забронированные (не завершённые).
  const active = mine.filter((r) => r.status === "accepted" || r.status === "slot_booked");

  return (
    <Layout>
      {error && <div className="error">{error}</div>}
      <div className="grid-2">
        {/* --- Лента открытых заявок --- */}
        <div className="panel">
          <div className="panel-title">
            <h2>Лента заявок</h2>
            <span className="units">{open.length} открытых</span>
          </div>
          {open.length === 0 ? (
            <div className="empty">Открытых заявок нет.</div>
          ) : (
            <div className="list">
              {open.map((r) => (
                <OpenRow key={r.id} r={r} onAccepted={load} />
              ))}
            </div>
          )}
        </div>

        {/* --- Мои рейсы: бронь слота + QR --- */}
        <div className="panel">
          <div className="panel-title">
            <h2>Мои рейсы</h2>
            <span className="units">{active.length} в работе</span>
          </div>
          {active.length === 0 ? (
            <div className="empty">Примите заявку из ленты слева, чтобы забронировать слот.</div>
          ) : (
            <div className="list">
              {active.map((r) => (
                <ActiveRow key={r.id} r={r} checkpoints={checkpoints} onBooked={load} />
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

// --- Открытая заявка: принять с указанием гос.номера ---
function OpenRow({ r, onAccepted }) {
  const [plate, setPlate] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function accept(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api(`/requests/${r.id}/accept`, {
        method: "POST",
        body: { truck_plate: plate },
      });
      onAccepted();
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="item">
      <div className="item-head">
        <span className="item-route">
          {r.origin} → {r.destination}
        </span>
        <span className="badge badge-open">{STATUS_RU[r.status]}</span>
      </div>
      <div className="item-meta">
        <span>
          {CARGO_RU[r.cargo_type]}, <b>{r.weight_t} т</b>
        </span>
        <span>
          на <b>{fmtDate(r.desired_date)}</b>
        </span>
        <span>{r.shipper.company || r.shipper.name}</span>
      </div>
      <form onSubmit={accept} className="row-2" style={{ marginTop: 10 }}>
        <input
          value={plate}
          onChange={(e) => setPlate(e.target.value)}
          placeholder="Гос. номер, 777 ABC 12"
          required
        />
        <button className="btn-primary" disabled={busy} type="submit">
          Принять
        </button>
      </form>
      {err && <div className="error">{err}</div>}
    </div>
  );
}

// --- Принятая/забронированная заявка: бронь слота или показ QR ---
function ActiveRow({ r, checkpoints, onBooked }) {
  const booking = r.assignment?.booking;
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
        </span>
        <span>
          борт: <b>{r.assignment.truck_plate}</b>
        </span>
      </div>

      {booking ? (
        <Pass booking={booking} />
      ) : (
        <BookingForm assignmentId={r.assignment.id} checkpoints={checkpoints} onBooked={onBooked} />
      )}
    </div>
  );
}

// --- Выбор узла/даты/слота и бронирование ---
function BookingForm({ assignmentId, checkpoints, onBooked }) {
  const [checkpointId, setCheckpointId] = useState("");
  const [date, setDate] = useState("");
  const [slots, setSlots] = useState([]);
  const [slotId, setSlotId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Подгружаем свободные слоты при выборе узла (и даты, если указана).
  useEffect(() => {
    if (!checkpointId) {
      setSlots([]);
      return;
    }
    const q = new URLSearchParams({ checkpoint_id: checkpointId });
    if (date) q.set("date", date);
    api(`/slots?${q.toString()}`)
      .then((s) => {
        setSlots(s);
        setSlotId("");
      })
      .catch((e) => setErr(e.message));
  }, [checkpointId, date]);

  async function book() {
    setErr("");
    setBusy(true);
    try {
      await api("/bookings", {
        method: "POST",
        body: { slot_id: Number(slotId), assignment_id: assignmentId },
      });
      onBooked();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ marginTop: 10 }}>
      <div className="row-2">
        <select value={checkpointId} onChange={(e) => setCheckpointId(e.target.value)}>
          <option value="">Выберите узел…</option>
          {checkpoints.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>

      {checkpointId && (
        <>
          <label>Свободный слот ({slots.length})</label>
          <select value={slotId} onChange={(e) => setSlotId(e.target.value)}>
            <option value="">Выберите время…</option>
            {slots.map((s) => (
              <option key={s.id} value={s.id}>
                {fmtSlot(s)} — свободно {s.available}/{s.capacity}
              </option>
            ))}
          </select>
        </>
      )}

      <button className="btn-primary btn-block" disabled={busy || !slotId} onClick={book}>
        Забронировать слот
      </button>
      {err && <div className="error">{err}</div>}
    </div>
  );
}

// --- QR-пропуск (раздел 5: судья сканирует и попадает на /pass/{token}) ---
function Pass({ booking }) {
  const url = `${window.location.origin}/pass/${booking.qr_token}`;
  return (
    <div style={{ marginTop: 12 }}>
      <div className="item-meta" style={{ marginBottom: 10 }}>
        <span>
          <b>{booking.checkpoint_name}</b>, {fmtSlot(booking)}
        </span>
      </div>
      <div className="qr-box">
        <QRCodeSVG value={url} size={168} level="M" />
      </div>
      <div className="qr-caption">
        <a href={url} target="_blank" rel="noreferrer">
          открыть пропуск ↗
        </a>
      </div>
    </div>
  );
}
