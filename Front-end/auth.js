// Shared sign-in state for every page. Asks the Flask backend (GET /api/auth/user) and, if signed in:
//  - sets <body data-auth="in"> so .auth-in-only parts (likes, comments, Mark as done) appear
//  - shows the user's name (#user-name) and turns #auth-btn into "Sign out"
//  - for admins (role: "admin"): sets <body data-role="admin"> and shows the "Admin" nav link (#admin-link)
// It does the same thing the page scripts on Home, Posts, Submit and Tasks do, so they don't clash.
(async () => {
  const btn = document.getElementById("auth-btn");
  try {
    const res = await fetch("/api/auth/user", { credentials: "include" });
    if (!res.ok) return; // 401 = not signed in, leave the page as it is
    const { user, role } = await res.json();

    document.body.dataset.auth = "in";

    if (role === "admin") {
      document.body.dataset.role = "admin";
      const adminLink = document.getElementById("admin-link");
      if (adminLink) adminLink.hidden = false;
    }

    const nameEl = document.getElementById("user-name");
    if (nameEl && user) {
      nameEl.textContent = user.name || user.email || ""; // textContent, so a name can't inject HTML
      nameEl.hidden = false;
    }

    if (btn) {
      btn.textContent = "Sign out";
      btn.href = "#";
      btn.onclick = async (e) => {
        e.preventDefault();
        try {
          await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
        } finally {
          window.location.reload();
        }
      };
    }
  } catch {
    // Backend not running (e.g. page opened without Flask): keep "Sign in"
  }
})();
