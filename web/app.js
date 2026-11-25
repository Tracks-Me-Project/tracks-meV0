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
  for (const id of ["login", "home", "boosters", "collection", "auctions", "auction", "bets"]) $(id).hidden = id !== screen;
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
  $("open-bets").replaceChildren();
  $("done-bets").replaceChildren();
  show("login");
}

// L'écran courant est dans l'adresse (#boosters) : retour du téléphone et F5 fonctionnent.
function currentScreen(quiet) {
  if (location.hash === "#boosters") return showBoosters();
  if (location.hash === "#collection") return showCollection();
  if (location.hash === "#auctions") return showAuctions(quiet);
  if (location.hash === "#bets") return showBets(quiet);
  if (location.hash.startsWith("#auction/")) return showAuction(location.hash.split("/")[1], quiet);
  return showHome(quiet);
}

async function refresh() {
  clearTimeout(timer);
  message();
  ledAuction = null; // l'alerte « dépassé » ne vaut que pour un détail resté ouvert
  if (!sessionStorage.getItem("token")) return show("login");
  try {
    await currentScreen(false);
  } catch (err) {
    fail(err);
  }
}

// Rafraîchissement automatique. « quiet » : demandé par la page, et non par le joueur : on ne
// redessine que si les données ont changé, et jamais pendant l'envoi d'une action.
const UNREACHABLE = "Serveur injoignable";
let pollTimer;
let pollMs;
let drawnData; // données de l'écran affiché, sans le détail des secondes
let renderId = 0; // une réponse silencieuse dépassée par une demande plus récente est ignorée
let ledAuction = null; // enchère affichée dont le joueur était en tête

const busy = () => document.querySelector("#auction-detail button:disabled") !== null;

// À appeler après la réponse du serveur : true s'il ne faut pas redessiner.
function skipDraw(quiet, id, data) {
  const next = JSON.stringify(data, (key, v) => (key.endsWith("seconds_left") ? v > 0 : v));
  if (quiet && (id !== renderId || busy() || next === drawnData)) return true;
  drawnData = next;
  return false;
}

async function poll() {
  clearTimeout(pollTimer);
  const idle = ["#boosters", "#collection"].includes(location.hash); // formulaires et décompte
  if (!idle && !document.hidden && sessionStorage.getItem("token") && !busy()) {
    try {
      await currentScreen(true);
      if ($("message").textContent === UNREACHABLE) message();
    } catch (err) {
      fail(err);
    }
  }
  clearTimeout(pollTimer); // une seule boucle, même si poll() a été relancé entre-temps
  pollTimer = setTimeout(poll, pollMs); // après la réponse : jamais deux requêtes empilées
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && pollMs) poll(); // retour sur l'onglet : mise à jour immédiate
});

function fail(err) {
  if (err.status === 401) return logout(); // jeton inconnu (base remise à zéro ?)
  const refusal = REFUSALS[err.message];
  if (refusal) return message(refusal(err.detail));
  message(err.status ? err.message : UNREACHABLE);
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
  BetsClosed: () => "Les paris sont fermés pour cette enchère.",
  BetOnOwnAuction: () => "Tu ne peux pas parier sur ta propre enchère.",
  BidderCannotBet: () => "Tu as enchéri : tu ne peux pas parier sur cette enchère.",
  AlreadyBet: () => "Tu as déjà parié sur cette enchère.",
  PredictionTooLow: (d) => `Pronostic trop bas : le prix a déjà atteint ${d.minimum}.`,
  TooManyOpenBets: () => "Tu as déjà le maximum de paris en cours.",
};

async function showHome(quiet) {
  const stale = watchScreen();
  const id = ++renderId;
  const me = await api("/me");
  if (stale() || skipDraw(quiet, id, me)) return;
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

async function showAuctions(quiet) {
  const stale = watchScreen();
  const id = ++renderId;
  const [me, rows] = await Promise.all([api("/me"), api("/auctions")]);
  if (stale() || skipDraw(quiet, id, [me, rows])) return;
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

// Le redessin ne doit pas effacer ce que le joueur saisit.
function typedInputs() {
  return [...document.querySelectorAll("#auction-detail input")]
    .filter((input) => input.value !== input.defaultValue || input === document.activeElement)
    .map((input) => ({
      name: input.name,
      value: input.value,
      min: Number(input.min),
      focused: input === document.activeElement,
    }));
}

function restoreInputs(typed) {
  for (const { name, value, min, focused } of typed) {
    const input = document.querySelector(`#auction-detail input[name="${name}"]`);
    if (!input) continue;
    // Un montant qui était valable et ne l'est plus laisse la place au nouveau minimum.
    const outdated = Number(value) >= min && Number(value) < Number(input.min);
    if (!outdated) input.value = value;
    if (focused) input.focus();
  }
}

async function showAuction(id, quiet) {
  const stale = watchScreen();
  const request = ++renderId;
  const [me, a] = await Promise.all([api("/me"), api(`/auctions/${encodeURIComponent(id)}`)]);
  if (stale() || skipDraw(quiet, request, [me, a])) return;
  if (ledAuction === a.id && a.leader_id !== me.id) {
    message("Tu as été dépassé : ta mise t'est rendue.");
  }
  ledAuction = a.leader_id === me.id ? a.id : null;
  const typed = typedInputs();
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
    element("p", a.my_prediction === null ? "" : `Ton pronostic : ${a.my_prediction}`, "badge"),
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
  if (open && a.seller_id !== me.id) {
    if (a.my_prediction !== null) {
      $("auction-detail").append(element("p", "Tu as parié : tu ne peux pas enchérir sur cette enchère."));
    } else if (a.leader_id !== me.id) {
      $("auction-detail").append(bidForm(a, me.available));
    }
  }
  if (open) $("auction-detail").append(...betSection(a, me, entries));
  show("auction");
  restoreInputs(typed);
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
rules.then((r) => {
  pollMs = r.interface.refresh_seconds * 1000;
  pollTimer = setTimeout(poll, pollMs);
});
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
    renderId++;
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
  Object.assign(amount, { type: "number", inputMode: "numeric", name: "amount", min, step: 1, defaultValue: min, required: true });
  const label = element("label", `Ta mise (minimum ${min}, disponible ${available})`);
  label.append(amount);
  const submit = element("button", "Miser");
  form.append(label, submit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = `Miser ${amount.value} sur « ${a.title} » ?`;
    const noBet = a.bets_seconds_left > 0 ? "\nTu ne pourras plus parier sur cette enchère." : "";
    if (!confirm(`${question}\nLa somme est bloquée tant que tu mènes.${noBet}`)) return;
    submit.disabled = true; // pas de double appui
    renderId++;
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

// Section « pari » du détail : le formulaire, ou la raison pour laquelle il n'y en a pas.
function betSection(a, me, entries) {
  const title = element("h3", "Pari sur le prix final");
  const why = (text) => [title, element("p", text)];
  if (a.seller_id === me.id) return why("C'est ta vente : tu ne peux pas parier dessus.");
  if (a.my_prediction !== null) {
    return why(`Tu as parié ${a.my_prediction} (mise ${a.bet_stake}). Résultat à la fin.`);
  }
  if (a.i_have_bid) return why("Tu as enchéri : tu ne peux pas parier sur cette enchère.");
  if (a.bets_seconds_left === 0) return why("Les paris sont fermés pour cette enchère.");

  const closes = element("p", "");
  entries.push({ el: closes, label: "Paris ouverts encore", seconds: a.bets_seconds_left });
  const form = document.createElement("form");
  const prediction = document.createElement("input");
  const min = a.current_price;
  Object.assign(prediction, { type: "number", inputMode: "numeric", name: "prediction", min, step: 1, defaultValue: min, required: true });
  const label = element("label", `Prix final prévu (mise ${a.bet_stake}, disponible ${me.available})`);
  label.append(prediction);
  const submit = element("button", "Parier");
  form.append(label, submit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = `Parier que « ${a.title} » se terminera à ${prediction.value} ?`;
    const warning = `Mise ${a.bet_stake}, bloquée jusqu'à la fin. Tu ne pourras plus enchérir ici.`;
    if (!confirm(`${question}\n${warning}`)) return;
    submit.disabled = true; // pas de double appui
    renderId++;
    message();
    try {
      const body = JSON.stringify({ prediction: Number(prediction.value) });
      await api(`/auctions/${a.id}/bets`, { method: "POST", body });
      await showAuction(a.id);
      message("Pari enregistré.", true);
    } catch (err) {
      await showAuction(a.id).catch(() => {});
      fail(err);
    }
  });
  return [title, closes, form];
}

// Les chiffres viennent des règles chargées par le serveur.
function betRules({ bet }) {
  const [first, second, third] = bet.podium_split_percent;
  return [
    `Mise fixe : ${bet.stake_percent_of_start_price} % du prix de départ.`,
    `Paris ouverts pendant ${bet.close_at_percent_of_duration} % de la durée, ${bet.max_open_per_account} en cours au plus.`,
    `Les 3 pronostics les plus proches se partagent ${bet.podium_share_percent} % de la cagnotte (${first} / ${second} / ${third}), les autres le reste.`,
    `À 3 parieurs : toute la cagnotte au podium. À 2 : ${bet.two_bettors_split_percent.join(" / ")}. Seul : remboursé.`,
    `Gain plafonné à ${bet.payout_cap_multiple} fois la mise. Enchère annulée ou invendue : remboursé.`,
  ];
}

function betResult(b) {
  if (b.auction_status === "cancelled") return "Enchère annulée : mise remboursée";
  if (b.auction_status === "unsold") return "Invendue : mise remboursée";
  const net = b.payout - b.stake;
  return `Prix final ${b.final_price} · gain ${b.payout} (net ${net > 0 ? "+" : ""}${net})`;
}

async function showBets(quiet) {
  const stale = watchScreen();
  const id = ++renderId;
  const [game, rows] = await Promise.all([rules, api("/bets")]);
  if (stale() || skipDraw(quiet, id, rows)) return;
  const entries = [];
  const lists = { open: [], done: [] };
  for (const b of rows) {
    const open = b.auction_status === "open";
    const item = document.createElement("li");
    const link = document.createElement("a");
    const state = element("small", open ? "" : betResult(b));
    link.href = `#auction/${b.auction_id}`;
    link.append(
      element("span", b.title),
      element("small", b.artist),
      element("small", `Ton pronostic : ${b.prediction} · mise ${b.stake}`),
      state,
    );
    item.append(link);
    lists[open ? "open" : "done"].push(item);
    if (open) entries.push({ el: state, label: "Fin dans", seconds: b.seconds_left });
  }
  for (const [name, items] of Object.entries(lists)) {
    $(`${name}-bets`).replaceChildren(...items);
    $(`${name}-bets-title`).hidden = items.length === 0;
  }
  $("bet-rules").replaceChildren(...betRules(game).map((text) => element("li", text)));
  $("no-bet").hidden = rows.length > 0;
  show("bets");
  countdown(entries, showBets);
}

async function cancelAuction(button, a) {
  if (!confirm(`Annuler la vente de « ${a.title} » ? Le titre revient dans ta collection.`)) return;
  button.disabled = true;
  renderId++;
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
