// Логин: брендовый сплит (коридор транзита) + форма + быстрый вход демо (раздел 4).
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../auth";

const DEMO = [
  { mail: "shipper@demo", icon: "📦", label: "Отправитель", hint: "создаёт заявки на перевозку" },
  { mail: "carrier@demo", icon: "🚛", label: "Перевозчик", hint: "бронирует слоты, берёт QR-пропуск" },
  { mail: "analyst@demo", icon: "📊", label: "Аналитик акимата", hint: "видит весь транзит области" },
];

const FEATS = [
  "Реальные узлы Мангистау на карте",
  "90 дней истории + прогноз загрузки",
  "Одна база — три роли — один деплой",
];

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // После перехода по ссылке из письма: /login?verified=1 (или 0 при ошибке).
  const [params] = useSearchParams();
  const verified = params.get("verified");

  async function submit(e, demoEmail) {
    if (e) e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(demoEmail || email, demoEmail ? "demo123" : password);
      // Дальше роутер сам отправит на кабинет по роли.
    } catch (err) {
      setError(err.message || "Не удалось войти");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap login-page">
      <div className="login-split">
        {/* Брендовый блок — виден на широком экране */}
        <aside className="login-hero">
          <div className="brand hero-brand">
            TransitFlow
            <small>Координация транзита · Мангистау</small>
          </div>

          {/* Анимированный коридор: поток грузов сквозь узлы */}
          <svg className="route" viewBox="0 0 400 70" role="img" aria-label="Коридор транзита">
            <line className="route-base" x1="40" y1="28" x2="360" y2="28" />
            <line className="route-flow" x1="40" y1="28" x2="360" y2="28" />
            {[
              [40, "Актау"],
              [200, "Бейнеу"],
              [360, "Болашак"],
            ].map(([x, name], i) => (
              <g key={name}>
                <circle className="node pulse" cx={x} cy="28" r="5" style={{ animationDelay: `${i * 0.5}s` }} />
                <text className="ntext" x={x} y="52">{name}</text>
              </g>
            ))}
          </svg>

          <p className="hero-tag">
            Диспетчерская «последней мили» авто-транзита: заявка, бронь слота на
            узле и QR-пропуск — в реальном времени.
          </p>

          <ul className="hero-feats">
            {FEATS.map((f) => (
              <li className="hero-feat" key={f}>
                <span className="dot" />
                {f}
              </li>
            ))}
          </ul>
        </aside>

        {/* Форма входа */}
        <div className="panel login-card">
          <div className="brand login-card-brand" style={{ marginBottom: 4 }}>
            TransitFlow
            <small>Координация транзита · Мангистау</small>
          </div>

          <div className="login-head">
            <h2>Вход</h2>
            <p>Войдите в кабинет или попробуйте демо-доступ.</p>
          </div>

          {verified === "1" && (
            <div className="verify-ok">Email подтверждён — теперь войдите.</div>
          )}
          {verified === "0" && (
            <div className="error">
              Ссылка подтверждения недействительна или уже использована.
            </div>
          )}

          <form onSubmit={submit}>
            <label>Email</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="shipper@demo"
              autoComplete="username"
            />
            <label>Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="demo123"
              autoComplete="current-password"
            />
            <button className="btn-primary btn-block" disabled={busy} type="submit">
              Войти
            </button>
          </form>

          <div className="divider">демо-доступ в один клик</div>

          <div className="quick">
            {DEMO.map(({ mail, icon, label, hint }) => (
              <button
                key={mail}
                className="quick-btn"
                disabled={busy}
                onClick={() => submit(null, mail)}
              >
                <span className="q-ico">{icon}</span>
                <span className="q-txt">
                  <b>{label}</b>
                  <span>{hint}</span>
                </span>
                <span className="q-arrow">→</span>
              </button>
            ))}
          </div>

          {error && <div className="error">{error}</div>}

          <p className="auth-switch">
            Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
