import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages 會把網站放在 https://<帳號>.github.io/<repo>/ 底下，
// build 時必須帶上 repo 名稱作為 base，否則 JS/CSS 的路徑會全部找不到。
// 本機開發仍用 "/"，避免要打 localhost:5173/WuWaGroup/ 才進得去。
const GITHUB_PAGES_BASE = "/WuWaGroup/";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? GITHUB_PAGES_BASE : "/",
  server: {
    port: 5173,
  },
}));
