import { getGreeting, getHealth, postEcho } from "./api.js";

const statusEl = document.getElementById("status");
const greetingForm = document.getElementById("greeting-form");
const greetingOutput = document.getElementById("greeting-output");
const echoForm = document.getElementById("echo-form");
const echoOutput = document.getElementById("echo-output");

/** Update the connection badge in the header. */
function setStatus(kind, label) {
  statusEl.className = `status status--${kind}`;
  statusEl.textContent = label;
}

/** Run an async action while disabling its submit button. */
async function withPending(button, action) {
  button.disabled = true;
  try {
    await action();
  } finally {
    button.disabled = false;
  }
}

/* --- Connection check on page load ------------------------------------- */
(async function checkHealth() {
  try {
    const health = await getHealth();
    setStatus("ok", `Connected · ${health.service}`);
  } catch {
    setStatus("error", "Backend unreachable");
  }
})();

/* --- GET example -------------------------------------------------------- */
greetingForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const button = greetingForm.querySelector("button");
  const name = new FormData(greetingForm).get("name") ?? "";

  withPending(button, async () => {
    try {
      const { message } = await getGreeting(name);
      greetingOutput.classList.remove("output--error");
      greetingOutput.textContent = message;
    } catch (error) {
      greetingOutput.classList.add("output--error");
      greetingOutput.textContent = error.message;
    }
  });
});

/* --- POST example ------------------------------------------------------- */
echoForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const button = echoForm.querySelector("button");
  const message = new FormData(echoForm).get("message") ?? "";

  withPending(button, async () => {
    try {
      const data = await postEcho({ message, sentAt: new Date().toISOString() });
      echoOutput.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      echoOutput.textContent = `Error: ${error.message}`;
    }
  });
});
