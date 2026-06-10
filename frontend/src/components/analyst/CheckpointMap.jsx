// Карта узлов Мангистау: CircleMarker-индикаторы с цветом по текущей загрузке.
// Тайлы CARTO dark — под палитру «диспетчерской». Иконки-картинки Leaflet
// не используем, чтобы не возиться с путями маркеров в сборке Vite.
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const KIND_RU = {
  sea_port: "Морской порт",
  road_border: "Автопереход",
  rail_border: "Ж/д переход",
  road_hub: "Автоузел",
};

// Цвета совпадают с CSS-переменными --load-* (низкая/средняя/высокая).
function loadColor(pct) {
  if (pct >= 85) return "#e2574c";
  if (pct >= 50) return "#f5a623";
  return "#3fb68b";
}

export default function CheckpointMap({ checkpoints }) {
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
      {checkpoints.map((cp) => (
        <CircleMarker
          key={cp.id}
          center={[cp.lat, cp.lng]}
          radius={10 + Math.min(10, cp.capacity_per_hour / 10)}
          pathOptions={{
            color: loadColor(cp.load_pct),
            fillColor: loadColor(cp.load_pct),
            fillOpacity: 0.45,
            weight: 2,
          }}
        >
          <Popup>
            <b>{cp.name}</b>
            <br />
            {KIND_RU[cp.kind] || cp.kind}
            <br />
            Сейчас: {cp.trucks_last_hour} маш/ч из {cp.capacity_per_hour}
            <br />
            Загрузка: {cp.load_pct}%
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
