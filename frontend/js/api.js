/**
 * Thin wrapper around fetch for talking to the Flask API.
 *
 * When the frontend is served by Flask, API_BASE stays relative.
 * If you run the frontend on another port, point this at Flask, e.g.
 *   export const API_BASE = "http://127.0.0.1:5000/api";
 */
export const API_BASE = "/api";

/**
 * Perform a JSON request and return the parsed response.
 *
 * @param {string} path - Path relative to API_BASE, e.g. "/health".
 * @param {RequestInit} [options] - Extra fetch options.
 * @returns {Promise<any>} Parsed JSON response.
 * @throws {Error} On network failure or a non-2xx response.
 */
export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    ...options,
  });

  const isJson = (response.headers.get("content-type") || "").includes(
    "application/json",
  );
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    const message =
      data && typeof data.error === "string"
        ? data.error
        : `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data;
}

/** GET /api/health */
export function getHealth() {
  return request("/health");
}

/** GET /api/greeting?name=... */
export function getGreeting(name) {
  const query = new URLSearchParams({ name }).toString();
  return request(`/greeting?${query}`);
}

/** POST /api/echo */
export function postEcho(payload) {
  return request("/echo", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
