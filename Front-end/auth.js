// Shows whether the visitor is signed in with Google.
// Asks the Flask backend (GET /api/auth/user) and, if signed in:
//  - changes the #auth-btn "Sign in" button to "Signed in"
//  - sets <body data-auth="in"> so .auth-in-only parts (likes, comments, Mark as done) appear
(async () => {
  const btn = document.getElementById("auth-btn");
  try {
    const res = await fetch("/api/auth/user", { credentials: "include" });
    if (!res.ok) return; // 401 = not signed in, leave the page as it is
    const { user } = await res.json();

    document.body.dataset.auth = "in";
    if (btn) {
      btn.textContent = "";
      const label = document.createElement("span");
      label.className = "auth-label";
      label.textContent = "Signed in";
      btn.append(label);
      // Show the Google account's name beside it (falls back to the email)
      const name = (user && (user.name || user.email)) || "";
      if (name) {
        const nameEl = document.createElement("span");
        nameEl.className = "auth-name";
        nameEl.textContent = name; // textContent, so a name can't inject HTML
        btn.append(nameEl);
      }
      btn.removeAttribute("href"); // already signed in, so it no longer links to Google
      btn.classList.add("is-signed-in");
      if (user && user.email) btn.title = `Signed in as ${user.email}`;
    }
  } catch {
    // Backend not running (e.g. page opened without Flask): keep "Sign in"
  }
})();
