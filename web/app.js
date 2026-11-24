// Jeton gardé par onglet (sessionStorage) : deux onglets = deux joueurs.
const $ = (id) => document.getElementById(id);
const message = (text = "") => { $("message").textContent = text; };

async function api(path, options = {}) {
  const token = sessionStorage.getItem("token");
  const headers = { "Content-Type": "application/json", ...(token && { Authorization: `Bearer ${token}` }) };
  const res = await fetch(path, { ...options, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(body.detail || "erreur"), { status: res.status });
  return body;
}

function show(screen) {
  $("login").hidden = screen !== "login";
  $("home").hidden = screen !== "home";
}

async function refresh() {
  if (!sessionStorage.getItem("token")) return show("login");
  try {
    const me = await api("/me");
    $("player-name").textContent = me.name;
    $("available").textContent = me.available;
    $("locked").textContent = me.locked;
    show("home");
  } catch (err) {
    if (err.status !== 401) return message("Serveur injoignable");
    sessionStorage.removeItem("token"); // jeton inconnu (base remise à zéro ?)
    show("login");
  }
}

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  message();
  try {
    const account = await api("/accounts", { method: "POST", body: JSON.stringify({ name: $("name").value }) });
    sessionStorage.setItem("token", account.token);
    await refresh();
  } catch (err) {
    message(err.status === 409 ? "Ce pseudo est déjà pris." : "Création impossible.");
  }
});

$("logout").addEventListener("click", () => {
  sessionStorage.removeItem("token");
  message();
  show("login");
});

api("/rules").then((r) => { $("rules-file").textContent = r.file; }).catch(() => {});
refresh();
