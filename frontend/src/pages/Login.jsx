// Логин: форма + кнопки быстрого входа демо-аккаунтов (раздел 4).
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth";

const DEMO = [
  ["shipper@demo", "Войти как отправитель"],
  ["carrier@demo", "Войти как перевозчик"],
  ["analyst@demo", "Войти как аналитик акимата"],
];

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
    <div className="login-wrap">
      <div className="panel login-card">
        <div className="brand" style={{ marginBottom: 4 }}>
          TransitFlow
          <small>Координация транзита · Мангистау</small>
        </div>

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

        <div className="divider">демо-доступ</div>

        <div className="quick">
          {DEMO.map(([mail, label]) => (
            <button
              key={mail}
              className="btn-ghost"
              disabled={busy}
              onClick={() => submit(null, mail)}
            >
              {label}
            </button>
          ))}
        </div>

        {error && <div className="error">{error}</div>}

        <p className="auth-switch">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </div>
    </div>
  );
}
