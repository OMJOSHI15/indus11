import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the dashboard needs no CORS setup.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // API_TARGET lets a second dashboard talk to a second API instance.
      "/api": process.env.API_TARGET ?? "http://localhost:8000",
    },
  },
});
