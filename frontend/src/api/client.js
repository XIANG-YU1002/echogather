// 沒帶 VITE_API_BASE_URL 時退回本機後端。
// 不給預設值的話，下一行的 new URL() 會在模組載入時就丟例外，整個 App 白屏。
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
const API_ORIGIN = new URL(BASE_URL).origin;

export function resolveMediaUrl(path) {
  if (!path) {
    return path;
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${API_ORIGIN}${path.startsWith("/") ? "" : "/"}${path}`;
}

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function buildUrl(path, params) {
  const url = new URL(BASE_URL.replace(/\/$/, "") + path);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }
  return url.toString();
}

export async function apiRequest(
  path,
  { method = "GET", body, params, token, isFormData = false } = {},
) {
  const headers = {};
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(buildUrl(path, params), {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const error = data?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "UNKNOWN_ERROR",
      error?.message ?? "發生錯誤，請稍後再試。",
      error?.details ?? null,
    );
  }

  return data;
}
