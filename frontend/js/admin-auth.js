/**
 * admin-auth.js — shared JWT auth for all admin pages.
 * Stores token in localStorage. Call requireAuth() on each admin page load.
 */

const ADMIN_TOKEN_KEY = "mahjong_admin_token";
const ADMIN_EXPIRY_KEY = "mahjong_admin_expires";

/** Get stored token or null */
export function getToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

/** Get Authorization header value */
export function authHeader() {
  const t = getToken();
  return t ? { "Authorization": `Bearer ${t}` } : {};
}

/** Store token + expiry */
export function saveToken(token, expiresIn) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
  localStorage.setItem(ADMIN_EXPIRY_KEY, String(Date.now() + expiresIn * 1000));
}

/** Clear token (logout) */
export function clearAuth() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
  localStorage.removeItem(ADMIN_EXPIRY_KEY);
}

/** Check if currently authenticated and not expired */
export function isAuthenticated() {
  const token = getToken();
  if (!token) return false;
  const expiry = Number(localStorage.getItem(ADMIN_EXPIRY_KEY) || 0);
  if (expiry && Date.now() > expiry - 30_000) return false; // 30s buffer
  return true;
}

/**
 * Redirect to login if not authenticated.
 * Call at the top of each admin page script.
 */
export function requireAuth(redirectTo = "admin-login.html") {
  if (!isAuthenticated()) {
    window.location.href = redirectTo;
    return false;
  }
  return true;
}

/** Login: POST credentials, store token, return {ok, error} */
export async function login(username, password) {
  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.detail || "登录失败" };
    saveToken(data.token, data.expires_in);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: "网络错误，请稍后重试" };
  }
}

/** Generic authenticated GET */
export async function apiGet(path) {
  const res = await fetch(path, { headers: authHeader() });
  if (res.status === 401) { clearAuth(); window.location.href = "admin-login.html"; }
  return res;
}

/** Generic authenticated PATCH (JSON body) */
export async function apiPatch(path, body) {
  const res = await fetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  });
  if (res.status === 401) { clearAuth(); window.location.href = "admin-login.html"; }
  return res;
}

/** Generic authenticated POST */
export async function apiPost(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  });
  if (res.status === 401) { clearAuth(); window.location.href = "admin-login.html"; }
  return res;
}

/** Generic authenticated DELETE */
export async function apiDelete(path) {
  const res = await fetch(path, {
    method: "DELETE",
    headers: { "Content-Type": "application/json", ...authHeader() },
  });
  if (res.status === 401) { clearAuth(); window.location.href = "admin-login.html"; }
  return res;
}
