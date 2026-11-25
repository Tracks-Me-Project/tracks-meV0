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
  for (const id of ["login", "home", "boosters"]) $(id).hidden = id !== screen;
  $("nav").hidden = screen === "login";
  for (const link of $("nav").children) {
    link.toggleAttribute("aria-current", link.hash === `#${screen}`);
  }
}

function logout() {
  sessionStorage.removeItem("token");
  clearTimeout(timer);
  $("drawn").replaceChildren(); // le tirage du joueur précédent
  show("login");
}

// L'écran courant est dans l'adresse (#boosters) : retour du téléphone et F5 fonctionnent.
async function refresh() {
  clearTimeout(timer);
  message();
  if (!sessionStorage.getItem("token")) return show("login");
  try {
    if (location.hash === "#boosters") await showBoosters();
    else await showHome();
  } catch (err) {
    fail(err);
  }
}

function fail(err) {
  if (err.status === 401) return logout(); // jeton inconnu (base remise à zéro ?)
  message(err.status ? err.message : "Serveur injoignable");
}

async function showHome() {
  const me = await api("/me");
  $("player-name").textContent = me.name;
  $("available").textContent = me.available;
  $("locked").textContent = me.locked;
  show("home");
}

let timer; // compte à rebours du prochain booster

async function showBoosters() {
  const { stock, max_stock, seconds_until_next: next } = await api("/boosters");
  $("stock").textContent = `${stock} / ${max_stock}`;
  $("open-booster").disabled = stock === 0;
  show("boosters");
  countdown(next);
}

// Le décompte est local ; à zéro on redemande au serveur, seul juge du stock.
function countdown(seconds) {
  clearTimeout(timer);
  if (seconds === null) return void ($("next-booster").textContent = "Stock plein");
  const rest = String(seconds % 60).padStart(2, "0");
  $("next-booster").textContent = `Prochain booster dans ${Math.floor(seconds / 60)}:${rest}`;
  timer = setTimeout(() => {
    if (seconds > 0) countdown(seconds - 1);
    else showBoosters().catch(fail);
  }, 1000);
}

// Une ligne par titre, « ×2 » pour un doublon dans le même booster. textContent : jamais de HTML.
function showDrawn(tracks) {
  const counts = new Map();
  for (const t of tracks) counts.set(t.id, { ...t, n: (counts.get(t.id)?.n ?? 0) + 1 });
  $("drawn").replaceChildren(...[...counts.values()].map((t) => {
    const item = document.createElement("li");
    const detail = document.createElement("small");
    item.textContent = t.n > 1 ? `${t.title} ×${t.n}` : t.title;
    detail.textContent = [t.artist, t.album, t.year].filter(Boolean).join(" · ");
    item.append(detail);
    return item;
  }));
}

$("open-booster").addEventListener("click", async () => {
  $("open-booster").disabled = true; // pas de double appui
  message();
  try {
    showDrawn((await api("/boosters/open", { method: "POST" })).tracks);
    await showBoosters();
  } catch (err) {
    await showBoosters().catch(() => {}); // remet stock et bouton à jour
    fail(err);
  }
});

window.addEventListener("hashchange", refresh);

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  message();
  location.hash = "";
  try {
    const account = await api("/accounts", { method: "POST", body: JSON.stringify({ name: $("name").value }) });
    sessionStorage.setItem("token", account.token);
    await refresh();
  } catch (err) {
    message(err.status === 409 ? "Ce pseudo est déjà pris." : "Création impossible.");
  }
});

$("logout").addEventListener("click", () => {
  message();
  location.hash = "";
  logout();
});

api("/rules").then((r) => { $("rules-file").textContent = r.file; }).catch(() => {});
refresh();
