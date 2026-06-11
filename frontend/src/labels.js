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
