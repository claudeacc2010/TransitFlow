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
  // Если на сервере включена верификация email — показываем «проверьте почту».
  const [sentTo, setSentTo] = useState("");

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await register({
        role: form.role,
        name: form.name,
        company: form.company || null,
        email: form.email,
        password: form.password,
      });
      if (data.verification_required) setSentTo(form.email);
      // Иначе роутер сам отправит на кабинет по роли.
    } catch (err) {
      setError(err.message || "Не удалось зарегистрироваться");
    } finally {
      setBusy(false);
    }
  }

  if (sentTo) {
    return (
      <div className="login-wrap">
        <div className="panel login-card">
          <div className="brand" style={{ marginBottom: 4 }}>
            TransitFlow
            <small>Подтвердите email</small>
          </div>
          <p>
            Мы отправили письмо на <b>{sentTo}</b>. Перейдите по ссылке из
            письма, чтобы активировать аккаунт, затем войдите.
          </p>
          <p className="auth-switch">
            <Link to="/login">К форме входа</Link>
          </p>
        </div>
      </div>
    );
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
