// Generates src/client/ (types, API functions, TanStack Query hooks) from openapi.json,
// which tools/export_openapi.py writes from the FastAPI app. Never edit src/client/ by hand.
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "./openapi.json",
  output: "src/client",
  plugins: [
    "@hey-api/client-fetch",
    "@hey-api/typescript",
    "@hey-api/sdk",
    "@tanstack/react-query",
  ],
});
