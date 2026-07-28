import { apiRequest } from "./client.js";

export function submitApplication(token, { reason } = {}) {
  return apiRequest("/group-leader-applications", {
    method: "POST",
    token,
    body: { reason: reason?.trim() ? reason.trim() : null },
  });
}

export function getMyApplication(token) {
  return apiRequest("/group-leader-applications/me", { token });
}
