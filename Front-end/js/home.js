// Renders the dynamic parts of the home page. Uses textContent (never innerHTML)
// so user-supplied names can't inject markup.

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function photo(url, alt, label) {
  const fig = el("figure");
  if (url) {
    const img = el("img");
    img.src = url;
    img.alt = alt;
    img.loading = "lazy";
    fig.appendChild(img);
  } else {
    const ph = el("div", "ba-placeholder");
    ph.setAttribute("role", "img");
    ph.setAttribute("aria-label", alt + " (no photo yet)");
    ph.textContent = "No photo";
    fig.appendChild(ph);
  }
  fig.appendChild(el("figcaption", "", label));
  return fig;
}

function formatDate(iso) {
  // Date-only strings ("2026-11-06") parse as UTC; read them as local so the day doesn't shift.
  const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso + "T00:00:00" : iso);
  return isNaN(d) ? iso : d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

async function renderAuth() {
  const user = await getSession();
  const btn = document.getElementById("auth-btn");
  if (!user) return;
  const name = document.getElementById("user-name");
  name.textContent = user.name;
  name.hidden = false;
  btn.textContent = "Sign out";
  btn.href = "logout.html";
  document.getElementById("admin-link").hidden = !user.is_admin;
}

async function renderLeaderboard() {
  // Renders the top 5 as a staircase. DOM order is rank 1 first (for screen
  // readers); CSS row-reverse puts rank 1 on the right as the tallest step.
  const list = document.getElementById("leaderboard");
  list.replaceChildren();
  try {
    const rows = await getLeaderboard(5);
    if (!rows.length) {
      list.appendChild(el("li", "stairs-status", "No points yet. Submit the first cleanup to take the top step."));
      return;
    }
    const max = Math.max(...rows.map((r) => r.points), 1);
    rows.forEach((r, i) => {
      const li = el("li", i === 0 ? "step is-leader" : "step");
      const label = el("div", "step-label");
      label.append(el("span", "step-name", r.name), el("span", "step-points", r.points + " pts"));
      const bar = el("div", "step-bar", String(i + 1));
      bar.setAttribute("aria-label", "Rank " + (i + 1));
      // Height tracks points, with a floor so low scores still read as a step.
      bar.style.setProperty("--h", Math.max(18, (r.points / max) * 78) + "%");
      bar.style.setProperty("--i", rows.length - 1 - i);
      li.append(label, bar);
      list.appendChild(li);
    });
  } catch {
    list.appendChild(el("li", "stairs-status", "The leaderboard didn't load. Refresh the page to try again."));
  }
}

async function renderSubmissions() {
  const wrap = document.getElementById("submissions");
  wrap.replaceChildren();
  try {
    const subs = await getRecentSubmissions(6);
    if (!subs.length) { wrap.appendChild(el("p", "muted", "No cleanups yet. Yours could be the first one here.")); return; }
    subs.forEach((s) => {
      const card = el("article", "sub-card");
      const pair = el("div", "ba-pair");
      pair.append(
        photo(s.before_url, "Before cleaning by " + s.user, "Before"),
        photo(s.after_url, "After cleaning by " + s.user, "After")
      );
      const meta = el("p", "sub-meta");
      const date = el("time", "", formatDate(s.created_at));
      date.dateTime = s.created_at;
      meta.append(el("strong", "", s.user), date);
      card.append(pair, meta);
      wrap.appendChild(card);
    });
  } catch {
    wrap.appendChild(el("p", "muted", "Recent cleanups didn't load. Refresh the page to try again."));
  }
}

renderAuth();
renderLeaderboard();
renderSubmissions();
