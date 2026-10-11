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
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  resolve: {
    // "@/components/ui/button" instead of "../../components/ui/button"
    alias: { "@": path.resolve(import.meta.dirname, "./src") },
  },
});
