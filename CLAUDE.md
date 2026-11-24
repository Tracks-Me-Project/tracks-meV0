# tracks-meV0

Serveur de jeu (proof of concept) : collection de tracks musicales, dont le cœur est constitué par les **enchères** et les **paris**. Les règles viennent d'une simulation faite dans un autre dépôt ; ce dépôt est le vrai serveur.

## Façon de travailler (obligatoire)

- Réponds en français.
- Propose un plan avant toute modification et attends ma validation.
- Petites étapes : un module ou une fonction à la fois. J'ai besoin de comprendre chaque ligne : explique tes choix et les alternatives écartées.
- Si je demande « explique », explique sans modifier le code.
- Aucune nouvelle dépendance sans me demander.
- Tous les paramètres du jeu dans un fichier de configuration, jamais en dur.
- Chaque fonction de logique métier a un test. Lance `ruff check .` et `pytest` avant de considérer une tâche terminée.
- Git : chaque étape ouvre une nouvelle branche ; une fois tests et ruff verts : commit, push, PR. Demande-moi confirmation avant de fusionner.
- Après chaque partie développée, explique l'aspect technique ET l'aspect fonctionnel.
- Les synthèses pour mon associé (profil marketing, non développeur) sont en langage clair, sans jargon.
- Règle ambiguë ou contradictoire dans les documents : demande-moi, ne choisis pas.
- Point juridique à faire vérifier avant mise en production : les paris (monnaie de jeu, mises, gains).

## Décisions techniques

- API seule, testée par scripts (pas d'interface pour l'instant).
- Python 3.12+, FastAPI, Postgres 16 (Docker), code typé.
- Comptes et monnaie minimaux : un jeton par joueur, pas de vraie authentification.
- Monnaie en entiers ; journal des opérations en ajout seul, le solde se déduit du journal.
- Stock de boosters calculé à la demande (pas de planificateur).
- Verrou de ligne à chaque mise (pas de double dépense).
- Clôture des enchères et paris par une petite boucle serveur ; règlement paresseux à la lecture.
- Horloge injectable pour les tests.
- Dépendances à valider une par une : FastAPI, Uvicorn, SQLAlchemy 2, Alembic, psycopg, pytest, httpx, ruff.

## Périmètre

Dans : boosters et collection, recyclage, enchères, paris au podium, joueurs virtuels de test.
Hors : quêtes, haut-faits, souhaits, jauge chaud/froid, tirage orienté (le tirage est uniforme), détection des tricheurs.

## Règles du jeu

Références : `docs/reference/regles_de_base.md`, `bilan_paris.md`, `resume_regles_de_base_associe.md`. En cas d'écart, ce qui suit (périmètre du PoC) prévaut sur ces documents.

- **Enchères** : durées 30 min, 1 h, 3 h, 6 h, 12 h. Chaque mise dépasse la précédente d'au moins 5 %. 5 enchères ouvertes au plus par compte. Aucun frais, aucune commission. Mise bloquée, rendue si on perd, retirée si on gagne. Le vendeur peut annuler pendant la première moitié de la durée.
- **Paris** : pronostic libre du prix final. Mise fixe = 10 % du prix de départ. 3 paris ouverts au plus. Fermés à 50 % de la durée. Pari ≥ prix courant. Podium : les 3 plus proches se partagent 80 % de la cagnotte (50/30/20), les autres parieurs le reste ; à 2 parieurs 70/30 ; parieur seul remboursé ; gain plafonné à 4× la mise ; arrondis détruits. Interdit : parier sur sa propre enchère, enchérir ET parier sur la même enchère.
- **Boosters** : 5 titres, 1 par heure, stock max 10, tirage uniforme dans le catalogue. Pas d'achat de boosters avec la monnaie.
- **Recyclage** : 1 titre doublon recyclé = 1 de monnaie, plafond quotidien en configuration (défaut 50, non décidé).

## Données

Le catalogue (MusicBrainz) n'est **pas versionné** sans mon accord (licence). À contrôler avant l'étape 2 : doublons de `recording_mbid`, valeurs vides.

## Plan

0. Squelette · 1. Comptes + journal de monnaie · 2. Catalogue, boosters, collection · 3. Recyclage · 4. Enchères · 5. Paris au podium · 6. Joueurs virtuels + tentatives d'abus (double dépense, mises simultanées).

## Commandes

- Base : `docker compose up -d` (Postgres sur le port 5442), puis `alembic upgrade head`.
- Tests : `ruff check . && pytest` (utilisent la base `tracks_test`, recréée à chaque session).
- API : `uvicorn tracks.main:app --port 8001` (le 8000 est souvent pris).
- Simulation : `python -m tracks.simulation.run --bots 20 --days 3 --seed 1` (base `tracks_sim`,
  vidée à chaque lancement ; dure environ 3 minutes).
