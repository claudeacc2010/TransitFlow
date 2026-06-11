// Карта узлов Мангистау: CircleMarker-индикаторы с цветом по очереди (§5) +
// транзитные коридоры со стрелками направления (совпадают с маршрутами §4).
// Тайлы CARTO dark — под палитру «диспетчерской». Иконки-картинки Leaflet
// не используем, чтобы не возиться с путями маркеров в сборке Vite.
import L from "leaflet";
import { Fragment } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  Tooltip,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

const KIND_RU = {
  sea_port: "Морской порт",
  road_border: "Автопереход",
  rail_border: "Ж/д переход",
  road_hub: "Автоузел",
};

// Транзитные коридоры между узлами (имена строго как в сиде). Стрелка —
// в направлении основного потока: из порта вглубь региона и к границам.
const CORRIDORS = [
  ["Порт Актау", "Узел Бейнеу (трасса Актау–Бейнеу)"],
  ["Порт Актау", "Порт Курык"],
  ["Порт Актау", "Погранпереход «Темир-Баба»"],
  ["Порт Курык", "Погранпереход «Темир-Баба»"],
  ["Порт Курык", "Ж/д переход «Болашак»"],
];

// §5: цвет узла/коридора по ожиданию в очереди (затор — главная боль кейса).
// >=8 ч — критично (красный), >=3 ч — напряжённо (оранжевый), иначе свободно.
function waitColor(hours) {
  if (hours >= 8) return "#e2574c";
  if (hours >= 3) return "#f5a623";
  return "#3fb68b";
}

// Экранный угол отрезка A→B (▶ по умолчанию смотрит вправо/на восток).
// На малых масштабах Web Mercator приближение «по координатам» достаточно.
function bearing(a, b) {
  const dx = b[1] - a[1];
  const dy = a[0] - b[0]; // экранный Y растёт вниз
  return (Math.atan2(dy, dx) * 180) / Math.PI;
}

function arrowIcon(angle, color) {
  return L.divIcon({
    className: "corridor-arrow",
    html: `<span style="color:${color};transform:rotate(${angle}deg)">➤</span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

export default function CheckpointMap({ checkpoints }) {
  const byName = Object.fromEntries(checkpoints.map((cp) => [cp.name, cp]));

  return (
    <MapContainer
      center={[43.9, 53.2]}
      zoom={6}
      className="map"
      scrollWheelZoom={false}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
      />

      {/* Коридоры между узлами: цвет = загрузка узла-назначения, стрелка = поток */}
      {CORRIDORS.map(([fromName, toName]) => {
        const from = byName[fromName];
        const to = byName[toName];
        if (!from || !to) return null;
        const a = [from.lat, from.lng];
        const b = [to.lat, to.lng];
        const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        const color = waitColor(to.est_wait_hours);
        return (
          <Fragment key={`${fromName}->${toName}`}>
            <Polyline
              positions={[a, b]}
              pathOptions={{ color, weight: 2, opacity: 0.5, dashArray: "6 8" }}
            />
            <Marker position={mid} icon={arrowIcon(bearing(a, b), color)} interactive={false} />
          </Fragment>
        );
      })}

      {/* Узлы: размер ~ ёмкость, цвет ~ ожидание в очереди */}
      {checkpoints.map((cp) => {
        const color = waitColor(cp.est_wait_hours);
        return (
          <CircleMarker
            key={cp.id}
            center={[cp.lat, cp.lng]}
            radius={10 + Math.min(10, cp.capacity_per_hour / 10)}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.5,
              weight: 2,
            }}
          >
            <Tooltip direction="top" offset={[0, -6]} opacity={1}>
              <b>{cp.name}</b> · {cp.est_wait_hours > 0 ? `≈ ${cp.est_wait_hours} ч` : "свободно"}
            </Tooltip>
            <Popup>
              <b>{cp.name}</b>
              <br />
              {KIND_RU[cp.kind] || cp.kind}
              <br />
              Пропускная способность: {cp.capacity_per_day} маш/сутки
              <br />
              Ожидают: <b>{cp.waiting_now}</b> · сейчас {cp.trucks_last_hour} маш/ч
              <br />
              Ожидание: <b>{cp.est_wait_hours >= 24 ? "24+ ч (критично)" : `≈ ${cp.est_wait_hours} ч`}</b>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
