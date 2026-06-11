// Русские подписи статусов/типов и форматтеры — общие для кабинетов.

export const STATUS_RU = {
  open: "Открыта",
  accepted: "Принята",
  slot_booked: "Слот забронирован",
  done: "Завершена",
  cancelled: "Отменена",
};

export const CARGO_RU = {
  container: "Контейнер",
  bulk: "Навалочный",
  liquid: "Наливной",
  general: "Генеральный",
  food: "Продукты питания",
  grain: "Зерно",
  oil_products: "Нефтепродукты",
  construction: "Стройматериалы",
  chemicals: "Химикаты",
};

export const CARGO_OPTIONS = [
  ["container", "Контейнер"],
  ["bulk", "Навалочный"],
  ["liquid", "Наливной"],
  ["general", "Генеральный"],
  ["food", "Продукты питания"],
  ["grain", "Зерно"],
  ["oil_products", "Нефтепродукты"],
  ["construction", "Стройматериалы"],
  ["chemicals", "Химикаты"],
];

export const URGENCY_RU = {
  normal: "Обычная",
  urgent: "Срочно",
};

// §3: подписи транспортных статусов и следующий шаг по цепочке.
export const SHIPMENT_RU = {
  confirmed: "Подтверждено",
  awaiting_loading: "Ожидает погрузки",
  in_transit: "В пути",
  at_checkpoint: "На пункте пропуска",
  at_port: "В порту",
  delivered: "Доставлено",
};

export const SHIPMENT_ORDER = [
  "confirmed",
  "awaiting_loading",
  "in_transit",
  "at_checkpoint",
  "at_port",
  "delivered",
];

export function nextShipmentStatus(current) {
  const i = SHIPMENT_ORDER.indexOf(current);
  return i >= 0 && i < SHIPMENT_ORDER.length - 1 ? SHIPMENT_ORDER[i + 1] : null;
}

// Полный жизненный цикл груза для степпера у отправителя.
export const SHIPMENT_STEPS = [
  "Создана",
  "Ищется перевозчик",
  ...SHIPMENT_ORDER.map((s) => SHIPMENT_RU[s]),
];

// Индекс текущего шага степпера по заявке (учитывает наличие назначения).
export function shipmentStepIndex(r) {
  if (!r.assignment) return 1; // ищется перевозчик
  return 2 + SHIPMENT_ORDER.indexOf(r.assignment.shipment_status);
}

// §2: цена в тенге с разделением разрядов («383 000 ₸»).
export function fmtMoney(v) {
  if (v == null) return "—";
  return `${Math.round(v).toLocaleString("ru-RU")} ₸`;
}

const pad = (n) => String(n).padStart(2, "0");

export function fmtDate(iso) {
  const d = new Date(iso);
  return `${pad(d.getUTCDate())}.${pad(d.getUTCMonth() + 1)}.${d.getUTCFullYear()}`;
}

export function fmtTime(iso) {
  const d = new Date(iso);
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

export function fmtSlot(slot) {
  return `${fmtDate(slot.starts_at)} · ${fmtTime(slot.starts_at)}–${fmtTime(slot.ends_at)} UTC`;
}

// Класс цвета загрузки слота по доле занятости (низкая/средняя/высокая).
export function loadClass(slot) {
  const used = slot.capacity ? slot.booked_count / slot.capacity : 0;
  if (used >= 0.85) return "load-high";
  if (used >= 0.5) return "load-mid";
  return "load-low";
}
