import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages 會把網站放在 https://<帳號>.github.io/<repo>/ 底下，
// build 時必須帶上 repo 名稱作為 base，否則 JS/CSS 的路徑會全部找不到。
// 本機開發仍用 "/"，避免要打 localhost:5173/echogather/ 才進得去。
//
// 這個值必須與 GitHub repo 名稱一致；repo 改名時要跟著改，
// 同時 Render 的 FRONTEND_BASE_URL 也要一起更新（重設密碼信的連結會用到）。
const GITHUB_PAGES_BASE = "/echogather/";

// 部署在自己網域根目錄的平台（Cloudflare Workers／Pages、Vercel…）要用 "/"，
// 在那邊的建置環境設 DEPLOY_BASE=/ 即可，GitHub Pages 不設就沿用上面的值。
// 兩個平台因此可以並存，不必二選一。
const deployBase = process.env.DEPLOY_BASE || GITHUB_PAGES_BASE;

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? deployBase : "/",
  server: {
    port: 5173,
  },
}));
