# Étape A03 : boosters

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a03-boosters` · **PR** : #13

## 1. Résumé fonctionnel
Un onglet « Boosters » (barre en bas de l'écran) montre le stock et le temps avant le prochain booster. On ouvre un booster et on voit les 5 titres reçus (titre, artiste, album, année) ; un titre sorti deux fois est marqué « ×2 ». Le bouton se grise quand le stock est vide.

## 2. Résumé technique
- `src/tracks/boosters.py` : `open_booster` renvoie les 5 titres, doublons répétés (avant : une fois chacun). La collection enregistrée ne change pas.
- `web/` : barre de navigation, écran Boosters, écran courant gardé dans l'adresse (`#boosters`), compte à rebours local qui redemande le stock au serveur à zéro.
- **Écartés** : faire retrouver les doublons par la page (fragile) ; interroger le serveur chaque seconde ; animation d'ouverture.

## 3. Guide de recette
Préparation : `docker compose up -d`, `alembic upgrade head`, `python -m tracks.catalogue` (une fois), puis `TRACKS_RULES_PATH=config/rules.essai.toml uvicorn tracks.main:app --port 8001`.

- [ ] Créer un joueur, onglet « Boosters » → « Stock : 10 / 10 », « Stock plein ».
- [ ] « Ouvrir un booster » → 5 titres (ou 4 avec un « ×2 », rare), stock 9 / 10, compte à rebours qui descend.
- [ ] Attendre la fin du compte à rebours (1 min en mode essai) → le stock remonte seul.
- [ ] Vider le stock → bouton grisé.
- [ ] Bouton retour du navigateur → écran précédent ; F5 sur `#boosters` → on reste sur Boosters.
- [ ] « Changer de joueur » puis nouveau joueur → pas de titres du joueur précédent à l'écran.
- [ ] Cas d'erreur : arrêter le serveur, « Ouvrir » → « Serveur injoignable ».
- [ ] Cas d'erreur : base sans catalogue → « catalogue vide ».

## 4. Points de vigilance
- **Risques** : le JavaScript n'a pas de test automatique.
- **Dette technique** : le dernier tirage disparaît après F5 (les titres sont bien dans la collection, visible en A04). Quitter l'écran pendant une requête en cours pourrait le réafficher (non observé).
- **Axes d'amélioration** : animation d'ouverture ; icône du site (`favicon.ico` répond 404, sans effet).
- **Questions ouvertes** : aucune.

## 5. Tests
- Couverts : 5 titres renvoyés (domaine et API), page servie avec le bouton. Parcours vérifié à la main par script dans Chromium (largeur 375 px) : création, ouverture, décompte, remontée du stock, stock vide, pas de défilement horizontal.
- `ruff check .` : ✅ · `pytest` : ✅ (115 tests)
