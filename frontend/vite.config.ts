import path from "node:path";
import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), babel({ presets: [reactCompilerPreset()] }), tailwindcss()],
  server: {
    // During development the browser talks to Vite only; /api requests go on to FastAPI.
    // changeOrigin false keeps the browser's Host header, so the API's CSRF check (Origin must
    // match Host) sees one site, exactly like production, where FastAPI serves page and API.
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  resolve: {
    // "@/components/ui/button" instead of "../../components/ui/button"
    alias: { "@": path.resolve(import.meta.dirname, "./src") },
  },
});
