import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { initSentry } from "./sentry";

// 在渲染前初始化 Sentry
initSentry();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
