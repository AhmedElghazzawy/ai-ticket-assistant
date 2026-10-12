import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { watchForExpiredSessions } from "./app/session-expiry";

watchForExpiredSessions();

const root = document.getElementById("root");
if (!root) throw new Error('index.html must contain <div id="root">');

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
