# Étape A02 : socle front

- **Statut** : ✅ terminé le 2026-11-24
- **Branche** : `a02-socle-front` · **PR** : #11 (correctif : #12)

## 1. Résumé fonctionnel
Le jeu a une première page, pensée pour le téléphone. On saisit un pseudo, on clique « Jouer », et on voit son solde (disponible et bloqué). « Changer de joueur » permet d'en créer un autre. Le pied de page indique quelles règles sont actives (normales ou essai). Chaque onglet du navigateur est un joueur distinct, ce qui permet de tester à plusieurs sur un seul ordinateur.

## 2. Résumé technique
- `src/tracks/main.py` : dossier `web/` servi sous `/app` (`StaticFiles`, déjà fourni par FastAPI, aucune dépendance), redirection `/` → `/app/`, nouveau `GET /rules` (nom du fichier de règles + règles).
- `web/index.html`, `web/style.css`, `web/app.js` : deux écrans (pseudo / accueil), un petit `api()` qui ajoute le jeton, retour à l'écran de pseudo si le jeton est refusé (401).
- Jeton dans `sessionStorage` (par onglet). Textes serveur insérés avec `textContent`, jamais en HTML.
- `tests/test_front.py` : 3 tests (redirection, page servie, `/rules`).
- **Écartés** : jeton en `localStorage` (tous les onglets seraient le même joueur) ; framework JS (outillage et dépendances) ; barre de navigation vide (arrive en A03).

## 3. Guide de recette
Préparation : `docker compose up -d`, `alembic upgrade head`, puis `TRACKS_RULES_PATH=config/rules.essai.toml uvicorn tracks.main:app --port 8001`.

- [ ] Ouvrir http://localhost:8001/ → redirigé vers `/app/`, écran « Choisis un pseudo ».
- [ ] Pied de page : « Règles : rules.essai.toml » (sans la variable : `rules.toml`).
- [ ] Saisir un pseudo, « Jouer » → pseudo affiché, Disponible 1000, Bloqué 0.
- [ ] Recharger la page (F5) → on reste connecté.
- [ ] Ouvrir un second onglet → écran de pseudo (autre joueur), pas de mélange avec le premier.
- [ ] Même pseudo dans le second onglet → « Ce pseudo est déjà pris. »
- [ ] « Changer de joueur » → retour à l'écran de pseudo.
- [ ] Réduire la fenêtre à ~375 px (ou outils développeur, mode mobile) → tout reste lisible, boutons larges, pas de défilement horizontal.
- [ ] Arrêter le serveur puis recharger → « Serveur injoignable » (et pas un écran blanc).
- [ ] Optionnel, sur téléphone : `--host 0.0.0.0` et adresse IP de l'ordinateur (sous WSL2, il faut en plus rediriger le port côté Windows : non vérifié).

## 4. Points de vigilance
- **Risques** : un joueur dont l'onglet est fermé est perdu (pas de reconnexion, assumé pour l'alpha locale). Le JavaScript n'est pas testé automatiquement (il faudrait Node et un outil de test) : seule la recette manuelle le couvre.
- **Dette technique** : un seul fichier JS ; à découper si A05 à A08 le rendent illisible.
- **Axes d'amélioration** : bouton pour afficher/copier son jeton ; installable sur l'écran d'accueil du téléphone (PWA) plus tard.
- **Questions ouvertes** : aucune.

## 5. Tests
- Couverts : redirection, page et script servis, `/rules`. Vérification de bout en bout du serveur réel en mode essai (curl) et de la syntaxe JS (`node --check`).
- Non couvert : le comportement dans un vrai navigateur (recette manuelle ci-dessus).
- `ruff check .` : ✅ · `pytest` : ✅ (114 tests)

## Correctif ultérieur (2026-11-25, branche `correctif-commit-avant-reponse`)
Dans un vrai navigateur, « Jouer » restait sur l'écran du pseudo : le serveur validait la transaction **après** avoir répondu, et `GET /me` arrivait avant (401). Le même défaut pouvait annoncer « succès » pour une mise jamais enregistrée (défaut présent depuis le PoC). Corrigé par `DbSession` (`src/tracks/api/deps.py`), couvert par `tests/test_commit.py`. Toute nouvelle route doit utiliser `DbSession`, jamais `Depends(get_session)` directement.
