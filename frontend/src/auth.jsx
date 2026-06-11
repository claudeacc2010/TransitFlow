// Контекст авторизации: токен в localStorage, пользователь — из /api/auth/me.
import { createContext, useContext, useEffect, useState } from "react";

import { api, clearToken, getToken, setToken } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // При загрузке: если есть токен — подтягиваем пользователя; иначе сразу готовы.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api("/auth/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const data = await api("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }

  // Регистрация отправителя/перевозчика. Если на сервере включена верификация
  // email, токена в ответе нет (verification_required: true) — пользователь
  // сначала подтверждает почту; иначе авто-логин как раньше.
  async function register(payload) {
    const data = await api("/auth/register", {
      method: "POST",
      body: payload,
      auth: false,
    });
    if (data.verification_required) return data;
    setToken(data.access_token);
    setUser(data.user);
    return data;
  }

  function logout() {
    clearToken();
    setUser(null);
  }

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
