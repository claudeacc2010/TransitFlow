// Шапка с брендом, ролью пользователя и выходом + контейнер контента.
import { useAuth } from "../auth";

const ROLE_RU = {
  shipper: "Отправитель",
  carrier: "Перевозчик",
  analyst: "Аналитик",
};

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="header">
        <div className="brand">
          TransitFlow
          <small>Координация транзита · Мангистау</small>
        </div>
        {user && (
          <div className="header-user">
            <div className="who">
              <b>{user.name}</b>
              <span>
                {ROLE_RU[user.role] || user.role}
                {user.company ? ` · ${user.company}` : ""}
              </span>
            </div>
            <button className="btn-ghost btn-sm" onClick={logout}>
              Выйти
            </button>
          </div>
        )}
      </header>
      <div className="container">{children}</div>
    </>
  );
}
