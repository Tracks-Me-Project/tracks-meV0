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
  for (const id of ["login", "home", "boosters", "collection", "auctions", "auction"]) $(id).hidden = id !== screen;
  $("nav").hidden = screen === "login";
  for (const link of $("nav").children) {
    // le détail d'une enchère reste sous l'onglet « Enchères »
    link.toggleAttribute("aria-current", link.hash === `#${screen === "auction" ? "auctions" : screen}`);
  }
}

function logout() {
  sessionStorage.removeItem("token");
  clearTimeout(timer);
  $("drawn").replaceChildren(); // le tirage et la collection du joueur précédent
  $("cards").replaceChildren();
  $("search").value = "";
  $("auction-list").replaceChildren();
  $("auction-detail").replaceChildren();
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
    else if (location.hash === "#auctions") await showAuctions();
    else if (location.hash.startsWith("#auction/")) await showAuction(location.hash.split("/")[1]);
    else await showHome();
  } catch (err) {
    fail(err);
  }
}

function fail(err) {
  if (err.status === 401) return logout(); // jeton inconnu (base remise à zéro ?)
  const refusal = REFUSALS[err.message];
  if (refusal) return message(refusal(err.detail));
  message(err.status ? err.message : "Serveur injoignable");
}

// Refus du jeu (nom envoyé par le serveur) en clair.
const REFUSALS = {
  AuctionNotFound: () => "Enchère introuvable.",
  AuctionClosed: () => "Cette enchère est terminée.",
  NotOwned: () => "Tu ne possèdes plus ce titre.",
  NotSeller: () => "Seul le vendeur peut annuler.",
  InvalidDuration: () => "Durée non autorisée.",
  StartPriceTooLow: (d) => `Prix de départ minimum : ${d.minimum}.`,
  TooManyOpen: () => "Tu as déjà le maximum d'enchères ouvertes.",
  CancelWindowPassed: () => "Le délai d'annulation est passé.",
  HasBids: () => "Annulation impossible : quelqu'un a déjà misé.",
  BidTooLow: (d) => `Mise trop basse : le minimum est maintenant ${d.minimum}.`,
  InsufficientFunds: () => "Solde disponible insuffisant.",
  AlreadyTopBidder: () => "Tu es déjà en tête.",
  OwnAuction: () => "Tu ne peux pas miser sur ta propre enchère.",
  BettorCannotBid: () => "Tu as parié sur cette enchère : tu ne peux pas y miser.",
};

async function showHome() {
  const me = await api("/me");
  $("player-name").textContent = me.name;
  $("available").textContent = me.available;
  $("locked").textContent = me.locked;
  show("home");
}

let timer; // le seul décompte actif : celui de l'écran affiché

// Rend une fonction : true si le joueur a changé d'écran ou de compte pendant une requête.
function watchScreen() {
  const at = location.hash;
  const token = sessionStorage.getItem("token");
  return () => location.hash !== at || sessionStorage.getItem("token") !== token;
}

function duration(seconds) {
  const two = (n) => String(n).padStart(2, "0");
  const h = Math.floor(seconds / 3600);
  const m = Math.floor(seconds / 60) % 60;
  return h ? `${h}:${two(m)}:${two(seconds % 60)}` : `${m}:${two(seconds % 60)}`;
}

// Décompte local d'après une échéance (un onglet en veille ne prend pas de retard).
// Quand l'un d'eux atteint zéro, on redemande au serveur, seul juge.
function countdown(entries, onZero) {
  clearTimeout(timer);
  const now = Date.now();
  const ends = entries.map((e) => ({ ...e, end: now + e.seconds * 1000 }));
  const tick = () => {
    let done = false;
    for (const { el, label, end } of ends) {
      const left = Math.max(0, Math.ceil((end - Date.now()) / 1000));
      el.textContent = `${label} ${duration(left)}`;
      done ||= left === 0;
    }
    if (ends.length) timer = setTimeout(done ? () => onZero().catch(fail) : tick, 1000);
  };
  tick();
}

async function showBoosters() {
  const stale = watchScreen();
  const { stock, max_stock, seconds_until_next: next } = await api("/boosters");
  if (stale()) return;
  $("stock").textContent = `${stock} / ${max_stock}`;
  $("open-booster").disabled = stock === 0;
  show("boosters");
  if (next === null) {
    clearTimeout(timer);
    $("next-booster").textContent = "Stock plein";
  } else {
    countdown([{ el: $("next-booster"), label: "Prochain booster dans", seconds: next }], showBoosters);
  }
}

function element(tag, text, className = "") {
  const el = document.createElement(tag);
  el.textContent = text; // jamais de HTML
  el.className = className;
  return el;
}

// Ce que cette enchère représente pour le joueur ; vide s'il n'est pas concerné.
function badge(a, myId) {
  if (a.status === "sold" && a.winner_id === myId) return "Tu as remporté cette enchère";
  if (a.seller_id === myId) return "Ton enchère";
  return a.status === "open" && a.leader_id === myId ? "Tu es en tête" : "";
}

async function showAuctions() {
  const stale = watchScreen();
  const [me, rows] = await Promise.all([api("/me"), api("/auctions")]);
  if (stale()) return;
  const entries = [];
  $("auction-list").replaceChildren(...rows.map((a) => {
    const item = document.createElement("li");
    const link = document.createElement("a");
    const left = element("small", "");
    link.href = `#auction/${a.id}`;
    link.append(
      element("span", a.title),
      element("small", a.artist),
      element("small", `Prix : ${a.current_price} · ${a.bid_count} mise(s)`),
      left,
      element("span", badge(a, me.id), "badge"),
    );
    item.append(link);
    entries.push({ el: left, label: "Fin dans", seconds: a.seconds_left });
    return item;
  }));
  $("no-auction").hidden = rows.length > 0;
  show("auctions");
  countdown(entries, showAuctions);
}

function auctionResult(a) {
  if (a.status === "sold") return `Vendue à ${a.winner_name} pour ${a.final_price}`;
  if (a.status === "unsold") return "Terminée sans mise : invendue";
  return "Annulée par le vendeur";
}

async function showAuction(id) {
  const stale = watchScreen();
  const [me, a] = await Promise.all([api("/me"), api(`/auctions/${encodeURIComponent(id)}`)]);
  if (stale()) return;
  const open = a.status === "open";
  const status = element("p", open ? "" : auctionResult(a));
  const list = document.createElement("dl");
  const rows = [
    ["Vendeur", a.seller_name],
    ["Prix de départ", a.start_price],
    ["Mises", a.bid_count],
    ...(open ? [
      ["Prix courant", a.current_price],
      ["Mise minimale", a.min_next_bid],
      ["Meneur", a.leader_name ?? "personne"],
    ] : []),
  ];
  for (const [label, value] of rows) list.append(element("dt", label), element("dd", value));
  $("auction-detail").replaceChildren(
    element("h2", a.title),
    element("p", [a.artist, a.album].filter(Boolean).join(" · ")),
    element("p", badge(a, me.id), "badge"),
    status,
    list,
  );
  const entries = open ? [{ el: status, label: "Fin dans", seconds: a.seconds_left }] : [];
  if (a.seller_id === me.id && a.cancel_seconds_left > 0) {
    const window = element("p", "");
    const button = element("button", "Annuler la vente", "secondary");
    button.type = "button";
    button.addEventListener("click", () => cancelAuction(button, a));
    $("auction-detail").append(window, button);
    entries.push({ el: window, label: "Annulable encore", seconds: a.cancel_seconds_left });
  }
  if (open && a.seller_id !== me.id && a.leader_id !== me.id) {
    $("auction-detail").append(bidForm(a, me.available));
  }
  show("auction");
  countdown(entries, () => showAuction(id));
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
  const game = await rules;
  // un de plus que la page : dit s'il reste quelque chose à afficher
  const rows = await api(`/collection?${new URLSearchParams({ q, limit: PAGE + 1, offset })}`);
  if (id !== loadId) return;
  const items = rows.slice(0, PAGE).map((t) => card(t, game));
  if (append) $("cards").append(...items);
  else $("cards").replaceChildren(...items);
  $("more").hidden = rows.length <= PAGE;
  $("empty").hidden = $("cards").children.length > 0;
  $("empty").textContent = q ? "Aucun titre ne correspond." : "Collection vide : ouvre un booster.";
}

function card(track, game) {
  const coins = game.recycling.coins_per_track;
  const item = trackItem(track, track.quantity);
  const duplicates = track.quantity - 1; // le dernier exemplaire ne se recycle pas
  const add = (label, n) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = `${label} (+${n * coins})`;
    button.addEventListener("click", () => recycleCard(item, track, n, game));
    item.append(button);
  };
  if (duplicates >= 1) add("Recycler 1", 1);
  if (duplicates >= 2) add(`Recycler les ${duplicates} doublons`, duplicates);
  item.append(sellForm(track, game.auction));
  return item;
}

// Volet natif <details> : prix et durées viennent des règles, le serveur reste seul juge.
function sellForm(track, { min_start_price: min, durations_minutes: durations }) {
  const box = document.createElement("details");
  const form = document.createElement("form");
  const price = document.createElement("input");
  Object.assign(price, { type: "number", inputMode: "numeric", min, step: 1, value: min, required: true });
  const duration = document.createElement("select");
  duration.append(...durations.map((m) => new Option(m < 60 ? `${m} min` : `${m / 60} h`, m)));
  const priceLabel = element("label", `Prix de départ (minimum ${min})`);
  priceLabel.append(price);
  const durationLabel = element("label", "Durée");
  durationLabel.append(duration);
  const submit = element("button", "Vendre");
  form.append(priceLabel, durationLabel, submit);
  box.append(element("summary", "Mettre aux enchères"), form);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const last = track.quantity === 1 ? "\nC'est ton dernier exemplaire." : "";
    const when = duration.selectedOptions[0].text;
    if (!confirm(`Vendre « ${track.title} » à partir de ${price.value}, pendant ${when} ?${last}`)) return;
    submit.disabled = true; // pas de double appui
    message();
    try {
      const body = JSON.stringify({
        recording_mbid: track.id,
        start_price: Number(price.value),
        duration_minutes: Number(duration.value),
      });
      const auction = await api("/auctions", { method: "POST", body });
      location.hash = `#auction/${auction.id}`;
    } catch (err) {
      submit.disabled = false;
      fail(err);
    }
  });
  return box;
}

async function recycleCard(item, track, n, game) {
  const coins = game.recycling.coins_per_track;
  const question = `Recycler ${n} exemplaire(s) de « ${track.title} » pour ${n * coins} pièce(s) ?`;
  if (!confirm(`${question}\nAction définitive.`)) return;
  const buttons = item.querySelectorAll("button");
  buttons.forEach((b) => { b.disabled = true; }); // pas de double appui
  message();
  try {
    const body = JSON.stringify({ recording_mbid: track.id, quantity: n });
    const done = await api("/collection/recycle", { method: "POST", body });
    item.replaceWith(card({ ...track, quantity: track.quantity - done.recycled }, game));
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

// Le solde et le minimum affichés sont indicatifs : seul le serveur accepte ou refuse la mise.
function bidForm(a, available) {
  const form = document.createElement("form");
  const amount = document.createElement("input");
  const min = a.min_next_bid;
  Object.assign(amount, { type: "number", inputMode: "numeric", min, step: 1, value: min, required: true });
  const label = element("label", `Ta mise (minimum ${min}, disponible ${available})`);
  label.append(amount);
  const submit = element("button", "Miser");
  form.append(label, submit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = `Miser ${amount.value} sur « ${a.title} » ?`;
    if (!confirm(`${question}\nLa somme est bloquée tant que tu mènes.`)) return;
    submit.disabled = true; // pas de double appui
    message();
    try {
      const body = JSON.stringify({ amount: Number(amount.value) });
      await api(`/auctions/${a.id}/bids`, { method: "POST", body });
      await showAuction(a.id);
      message("Mise enregistrée.", true);
    } catch (err) {
      await showAuction(a.id).catch(() => {}); // état à jour : surenchère, fin…
      fail(err);
    }
  });
  return form;
}

async function cancelAuction(button, a) {
  if (!confirm(`Annuler la vente de « ${a.title} » ? Le titre revient dans ta collection.`)) return;
  button.disabled = true;
  message();
  try {
    await api(`/auctions/${a.id}/cancel`, { method: "POST" });
    await showAuction(a.id);
    message("Vente annulée.", true);
  } catch (err) {
    await showAuction(a.id).catch(() => {}); // état à jour : mise reçue, délai passé…
    fail(err);
  }
}

window.addEventListener("hashchange", () => {
  $("auction-detail").replaceChildren();
  refresh();
});

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
