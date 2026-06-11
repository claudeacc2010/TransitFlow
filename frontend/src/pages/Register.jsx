// Регистрация отправителя/перевозчика. Аналитик — внутренняя роль акимата,
// через эту форму недоступен (ограничено и на бэкенде). После успеха роутер
// сам уводит в кабинет по роли.
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth";

const ROLES = [
  ["shipper", "Отправитель"],
  ["carrier", "Перевозчик"],
];

export default function Register() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    role: "shipper",
    name: "",
    company: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register({
        role: form.role,
        name: form.name,
        company: form.company || null,
        email: form.email,
        password: form.password,
      });
      // Дальше роутер сам отправит на кабинет по роли.
    } catch (err) {
      setError(err.message || "Не удалось зарегистрироваться");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="panel login-card">
        <div className="brand" style={{ marginBottom: 4 }}>
          TransitFlow
          <small>Регистрация участника</small>
        </div>

        <form onSubmit={submit}>
          <label>Я регистрируюсь как</label>
          <div className="role-toggle">
            {ROLES.map(([value, label]) => (
              <button
                type="button"
                key={value}
                className={form.role === value ? "active" : ""}
                onClick={() => setForm((f) => ({ ...f, role: value }))}
              >
                {label}
              </button>
            ))}
          </div>

          <label>Имя</label>
          <input value={form.name} onChange={set("name")} placeholder="Айбек Нурланов" />

          <label>Компания (необязательно)</label>
          <input value={form.company} onChange={set("company")} placeholder="ТОО «КаспийТранс»" />

          <label>Email</label>
          <input
            value={form.email}
            onChange={set("email")}
            placeholder="you@company.kz"
            autoComplete="username"
          />

          <label>Пароль</label>
          <input
            type="password"
            value={form.password}
            onChange={set("password")}
            placeholder="минимум 6 символов"
            autoComplete="new-password"
          />

          <button className="btn-primary btn-block" disabled={busy} type="submit">
            {busy ? "Создаём…" : "Зарегистрироваться"}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        <p className="auth-switch">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  );
}
