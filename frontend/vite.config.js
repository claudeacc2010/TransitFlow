import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api и /pass проксируем на бэкенд (uvicorn :8000) при локальной разработке.
// На Railway фронт-билд раздаётся статикой с того же домена — прокси не нужен.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/pass": "http://localhost:8000",
    },
  },
});
