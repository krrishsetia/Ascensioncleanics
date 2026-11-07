// All back-end calls live here. Set USE_MOCK = false once the Flask API is running.
const USE_MOCK = true;
const API_BASE = "http://localhost:5000"; // Flask dev server

const MOCK = {
  me: { name: "Ricky", is_admin: false },
  leaderboard: [
    { name: "Ava", points: 120 },
    { name: "Ben", points: 95 },
    { name: "Chloe", points: 80 },
    { name: "Dev", points: 55 },
    { name: "Ellis", points: 40 },
  ],
  submissions: [
    { id: 1, user: "Ava", before_url: "", after_url: "", created_at: "2026-11-06" },
    { id: 2, user: "Ben", before_url: "", after_url: "", created_at: "2026-11-05" },
    { id: 3, user: "Chloe", before_url: "", after_url: "", created_at: "2026-11-04" },
    { id: 4, user: "Dev", before_url: "", after_url: "", created_at: "2026-11-03" },
    { id: 5, user: "Ellis", before_url: "", after_url: "", created_at: "2026-11-02" },
    { id: 6, user: "Ava", before_url: "", after_url: "", created_at: "2026-11-01" },
  ],
};

async function apiGet(path) {
  const res = await fetch(API_BASE + path, { credentials: "include" });
  if (!res.ok) throw new Error(res.status + " " + path);
  return res.json();
}

// Returns the signed-in user, or null if signed out.
async function getSession() {
  if (USE_MOCK) return null; // change to MOCK.me to preview the signed-in state
  try { return await apiGet("/api/me"); } catch { return null; }
}

async function getLeaderboard(limit = 5) {
  if (USE_MOCK) return MOCK.leaderboard.slice(0, limit);
  return apiGet("/api/leaderboard?limit=" + limit);
}

async function getRecentSubmissions(limit = 6) {
  if (USE_MOCK) return MOCK.submissions.slice(0, limit);
  return apiGet("/api/submissions?limit=" + limit);
}
