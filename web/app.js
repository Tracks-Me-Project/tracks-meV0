// Jeton gardé par onglet (sessionStorage) : deux onglets = deux joueurs.
const $ = (id) => document.getElementById(id);
const message = (text = "", ok = false) => {
  $("message").textContent = text;
  $("message").classList.toggle("ok", ok);
};

async function api(path, options = {}) {
  const token = sessionStorage.getItem("token");
  const headers = { "Content-Type": "application/json", ...(token && { Authorization: `Bearer ${token}` }) };
  const res = await fetch(path, { ...options, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    // detail : texte, objet {error, ...} (refus du jeu) ou liste (saisie invalide)
    const { detail } = body;
    const text = typeof detail === "string" ? detail : detail?.error || "erreur";
    throw Object.assign(new Error(text), { status: res.status, detail });
  }
  return body;
}

function show(screen) {
  for (const id of ["login", "home", "boosters", "collection"]) $(id).hidden = id !== screen;
  $("nav").hidden = screen === "login";
  for (const link of $("nav").children) {
    link.toggleAttribute("aria-current", link.hash === `#${screen}`);
  }
}

function logout() {
  sessionStorage.removeItem("token");
  clearTimeout(timer);
  $("drawn").replaceChildren(); // le tirage et la collection du joueur précédent
  $("cards").replaceChildren();
  $("search").value = "";
  show("login");
}

// L'écran courant est dans l'adresse (#boosters) : retour du téléphone et F5 fonctionnent.
async function refresh() {
  clearTimeout(timer);
  message();
  if (!sessionStorage.getItem("token")) return show("login");
  try {
    if (location.hash === "#boosters") await showBoosters();
    else if (location.hash === "#collection") await showCollection();
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

// Titre (« ×2 » si plusieurs) puis artiste · album · année. textContent : jamais de HTML.
function trackItem(t, n) {
  const item = document.createElement("li");
  const name = document.createElement("span");
  const detail = document.createElement("small");
  name.textContent = n > 1 ? `${t.title} ×${n}` : t.title;
  detail.textContent = [t.artist, t.album, t.year].filter(Boolean).join(" · ");
  item.append(name, detail);
  return item;
}

// Une ligne par titre, « ×2 » pour un doublon dans le même booster.
function showDrawn(tracks) {
  const counts = new Map();
  for (const t of tracks) counts.set(t.id, { ...t, n: (counts.get(t.id)?.n ?? 0) + 1 });
  $("drawn").replaceChildren(...[...counts.values()].map((t) => trackItem(t, t.n)));
}

const PAGE = 50;
const rules = api("/rules").then((r) => { $("rules-file").textContent = r.file; return r.rules; });
rules.catch(() => {});
let loadId = 0; // une réponse en retard (frappe suivante) est ignorée

async function showCollection() {
  show("collection");
  await loadCards(false);
}

async function loadCards(append) {
  const id = ++loadId;
  const q = $("search").value.trim();
  const offset = append ? $("cards").children.length : 0;
  const coins = (await rules).recycling.coins_per_track;
  // un de plus que la page : dit s'il reste quelque chose à afficher
  const rows = await api(`/collection?${new URLSearchParams({ q, limit: PAGE + 1, offset })}`);
  if (id !== loadId) return;
  const items = rows.slice(0, PAGE).map((t) => card(t, coins));
  if (append) $("cards").append(...items);
  else $("cards").replaceChildren(...items);
  $("more").hidden = rows.length <= PAGE;
  $("empty").hidden = $("cards").children.length > 0;
  $("empty").textContent = q ? "Aucun titre ne correspond." : "Collection vide : ouvre un booster.";
}

function card(track, coins) {
  const item = trackItem(track, track.quantity);
  const duplicates = track.quantity - 1; // le dernier exemplaire ne se recycle pas
  const add = (label, n) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = `${label} (+${n * coins})`;
    button.addEventListener("click", () => recycleCard(item, track, n, coins));
    item.append(button);
  };
  if (duplicates >= 1) add("Recycler 1", 1);
  if (duplicates >= 2) add(`Recycler les ${duplicates} doublons`, duplicates);
  return item;
}

async function recycleCard(item, track, n, coins) {
  const question = `Recycler ${n} exemplaire(s) de « ${track.title} » pour ${n * coins} pièce(s) ?`;
  if (!confirm(`${question}\nAction définitive.`)) return;
  const buttons = item.querySelectorAll("button");
  buttons.forEach((b) => { b.disabled = true; }); // pas de double appui
  message();
  try {
    const body = JSON.stringify({ recording_mbid: track.id, quantity: n });
    const done = await api("/collection/recycle", { method: "POST", body });
    item.replaceWith(card({ ...track, quantity: track.quantity - done.recycled }, coins));
    message(`+${done.coins} pièce(s). Plafond restant aujourd'hui : ${done.remaining_cap_today}.`, true);
  } catch (err) {
    buttons.forEach((b) => { b.disabled = false; });
    const d = err.detail;
    if (d?.remaining !== undefined) message(`Plafond quotidien : il reste ${d.remaining} pièce(s).`);
    else if (d?.available !== undefined) message(`Seulement ${d.available} doublon(s) disponible(s).`);
    else fail(err);
  }
}

let typing; // courte pause dans la frappe avant d'interroger le serveur
$("search").addEventListener("input", () => {
  clearTimeout(typing);
  typing = setTimeout(() => { message(); loadCards(false).catch(fail); }, 300);
});
$("more").addEventListener("click", () => loadCards(true).catch(fail));

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

refresh();
