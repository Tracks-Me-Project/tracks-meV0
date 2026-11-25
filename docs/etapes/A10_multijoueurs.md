# Étape A10 : scénario multi-joueurs

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a10-multijoueurs` · **PR** : #20

## 1. Résumé fonctionnel
Des joueurs virtuels peuvent jouer sur le serveur en même temps que de vrais joueurs : ils ouvrent des boosters, vendent, misent, parient, recyclent et annulent. Une commande vérifie après une partie que les comptes sont justes. Un mode d'emploi guide l'installation puis une partie d'environ 15 minutes : `docs/guide_test_alpha.md`.

## 2. Résumé technique
- `src/tracks/simulation/live.py` : réutilise les profils de `bots.py` ; joue uniquement par l'API, sur un serveur réel et en temps réel ; refuse de démarrer si ses règles diffèrent de celles du serveur.
- `src/tracks/simulation/checks.py` : commande `python -m tracks.simulation.checks`, en lecture seule, sur une photo unique de la base ; sans le comptage des cartes.
- `tests/test_live.py` : 3 tests.
- **Écartés** : option dans la simulation (elle vide sa base) ; bots intégrés au serveur ; nouveaux comportements de bots.

## 3. Guide de recette
Préparation : partie 1 de `docs/guide_test_alpha.md`.

- [ ] Lancer les bots → leurs pseudos s'affichent, puis un résumé à chaque tour actif.
- [ ] Dans la page, des ventes de bots apparaissent ; vendre un titre → ils misent parfois dessus.
- [ ] Ctrl+C → « Bots arrêtés. »
- [ ] Bots sans `TRACKS_RULES_PATH` alors que le serveur est en mode essai → message, arrêt immédiat.
- [ ] Bots sans serveur → « Serveur injoignable … ».
- [ ] `python -m tracks.simulation.checks` après la partie → « OK ».
- [ ] Dérouler la partie 2 du guide avec une personne non technique.

## 4. Points de vigilance
- **Risques** : chaque lancement crée de nouveaux comptes (remise à zéro de la base pour nettoyer). `--url` permet de viser un autre serveur : les bots y créeraient des comptes.
- **Dette technique** : les bots jouent au hasard (prix et pronostics sans logique) : ils servent à animer, pas à juger l'équilibre. Leurs ventes encore ouvertes restent après leur arrêt (réglées par le serveur).
- **Axes d'amélioration** : bots plus réalistes ; contrôle du nombre de cartes en journalisant les ouvertures de boosters.

## 5. Tests
- Couverts : les bots jouent par l'API sans erreur serveur et les comptes restent cohérents ; refus si règles différentes ; la commande de contrôle détecte un compte falsifié. Essai réel de 90 s contre un serveur : 28 tours, 15 ventes, 21 mises, 20 paris, aucune erreur 500, contrôle « OK », arrêt propre.
- Non vérifié : les commandes du guide exécutées à la suite sur une machine neuve.
- `ruff check .` : ✅ · `pytest` : ✅ (134 tests)
