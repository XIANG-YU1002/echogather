import js from "@eslint/js";
import globals from "globals";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

/**
 * 最小 ESLint 設定（使用者 2026-07-31 授權加入）。
 *
 * 目的只有一個：擋下 Vite build 擋不住、只在使用者點下去那一刻才炸的錯誤——
 * 未定義的變數、忘記 import 的元件、Hook 用錯位置。專案已經因為這類問題
 * 踩過三次（見進度檔第 8、11 批）。
 *
 * 刻意不做風格檢查（縮排、引號、分號一律不管），避免對既有程式碼產生大量
 * 無意義的噪音，也不需要跟編輯器設定打架。
 *
 * 用法：npm run lint
 */
export default [
  { ignores: ["dist/**", "node_modules/**"] },
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { react, "react-hooks": reactHooks },
    settings: { react: { version: "detect" } },
    rules: {
      ...js.configs.recommended.rules,

      // 真正要擋的三類錯誤
      "no-undef": "error",
      "react/jsx-no-undef": "error",
      "react-hooks/rules-of-hooks": "error",

      // 沒有這條，只在 JSX 裡用到的元件會全部被誤判成「未使用的 import」
      "react/jsx-uses-vars": "error",

      // 有價值但不該擋住開發的，降為警告
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "react-hooks/exhaustive-deps": "warn",

      // 風格類一律關閉
      "no-empty": "off",
      "no-console": "off",
      // 中文排版會刻意用全形空格排版（例如「公告列表　共 N 則」），只檢查程式碼本身
      "no-irregular-whitespace": ["error", { skipStrings: true, skipJSXText: true, skipComments: true }],
    },
  },
];
