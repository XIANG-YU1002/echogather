import { apiRequest } from "./client.js";

export function sendVerificationCode(email) {
  return apiRequest("/auth/verification-codes", { method: "POST", body: { email } });
}

export function requestPasswordReset(email) {
  return apiRequest("/auth/password-reset-requests", { method: "POST", body: { email } });
}

export function verifyPasswordResetToken(token) {
  return apiRequest(`/auth/password-reset-tokens/${encodeURIComponent(token)}`);
}

export function resetPassword({ token, password, passwordConfirmation }) {
  return apiRequest("/auth/password-reset", {
    method: "POST",
    body: {
      token,
      password,
      password_confirmation: passwordConfirmation,
    },
  });
}

export function register(payload) {
  return apiRequest("/auth/register", { method: "POST", body: payload });
}

export function login(payload) {
  return apiRequest("/auth/login", { method: "POST", body: payload });
}

export function getCurrentSession(token) {
  return apiRequest("/auth/me", { token });
}
