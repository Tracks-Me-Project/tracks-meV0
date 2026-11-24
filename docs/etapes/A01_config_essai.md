# Étape A01 : configuration d'essai

- **Statut** : ✅ terminé le 2026-11-24
- **Branche** : `a01-config-essai` · **PR** : #10

## 1. Résumé fonctionnel
On peut lancer le jeu en « mode essai » : les enchères durent 1, 2, 5, 10 ou 30 minutes (au lieu de 30 minutes à 12 heures) et un booster arrive chaque minute (au lieu de chaque heure). Toutes les autres règles (pourcentages, plafonds, monnaie de départ) sont identiques, donc on teste les vraies règles, seulement plus vite.

## 2. Résumé technique
- `src/tracks/config.py` : nouveau réglage `rules_path` (variable `TRACKS_RULES_PATH`), par défaut `config/rules.toml`. `get_rules()` charge ce fichier. Aucune logique métier modifiée.
- `config/rules.essai.toml` : copie de `rules.toml` avec 3 valeurs changées (durées d'enchères, minutes par booster, intervalle de la boucle de règlement à 2 s).
- `tests/test_config.py` : 2 tests (le fichier d'essai est valide et ne diffère que par les durées ; la variable d'environnement change bien les règles lues).
- **Écarté** : surcharge partielle (fusion de dictionnaires, plus de code) ; endpoint qui avance l'horloge (plus puissant mais plus de code).

## 3. Guide de recette
Préparation : `docker compose up -d`, `alembic upgrade head`.

- [ ] Lancer `TRACKS_RULES_PATH=config/rules.essai.toml uvicorn tracks.main:app --port 8001`, créer un compte (`POST /accounts`), `GET /boosters` → un booster crédité par minute (temps entre deux crédits : 1 min).
- [ ] Créer une enchère avec `duration_minutes: 1` → acceptée ; elle se règle seule environ 1 min plus tard.
- [ ] Créer une enchère avec `duration_minutes: 720` en mode essai → refusée (durée invalide).
- [ ] Relancer **sans** la variable → `duration_minutes: 720` est de nouveau acceptée, `1` refusée.
- [ ] Une faute de frappe dans `rules.essai.toml` (clé inconnue) → le serveur refuse de démarrer.

## 4. Points de vigilance
- **Risques** : oublier la variable donne les durées normales sans avertissement (le front A02 affichera le mode actif). Même base pour les deux modes : des enchères courtes et longues peuvent coexister.
- **Dette technique** : le fichier d'essai est une copie ; si on ajoute une règle à `rules.toml`, il faut l'ajouter dans `rules.essai.toml` (le chargeur refuse un fichier incomplet, donc l'oubli se voit tout de suite).
- **Axes d'amélioration** : base dédiée `tracks_essai` si le mélange gêne.

## 5. Tests
- Couverts : validité du fichier d'essai, écart limité aux durées, prise en compte de `TRACKS_RULES_PATH`.
- `ruff check .` : ✅ · `pytest` : ✅ (111 tests)
