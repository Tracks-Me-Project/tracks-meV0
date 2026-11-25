# Étape A04 : collection et recyclage

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a04-collection` · **PR** : PRNUM

## 1. Résumé fonctionnel
Un onglet « Collection » liste les titres du joueur (avec « ×N » pour les doublons), 50 à la fois. Un champ cherche par titre, artiste ou album. Chaque doublon peut être recyclé en monnaie (un seul ou tous), après confirmation ; le dernier exemplaire est protégé. Le jeu indique la monnaie gagnée et ce qui reste du plafond du jour.

## 2. Résumé technique
- `src/tracks/collection.py` : `list_collection` accepte `query` (titre, artiste ou album ; casse ignorée ; `%` et `_` traités comme du texte).
- `GET /collection?q=` : 100 caractères au plus, caractère nul refusé. Sans `q`, rien ne change.
- `web/` : écran Collection, recherche (pause de 300 ms, réponses en retard ignorées), « Afficher plus », confirmation native (`confirm`), message collé au-dessus de la barre, erreurs « objet » du serveur lisibles.
- **Écartés** : filtrer dans la page (ne verrait que les titres chargés) ; fenêtre de confirmation maison ; ignorer les accents (extension `unaccent` + migration) ; commande offrant des doublons (cartes hors règles).

## 3. Guide de recette
Préparation : mode essai, voir les commandes dans `CLAUDE.md` (base `tracks_essai`).

- [ ] Nouveau joueur, onglet « Collection » → « Collection vide : ouvre un booster. »
- [ ] Ouvrir plusieurs boosters, revenir → titres listés, certains avec « ×2 » ou plus.
- [ ] Chercher un morceau d'artiste ou d'album, en minuscules → la liste se réduit ; texte inconnu → « Aucun titre ne correspond. »
- [ ] Un titre en un seul exemplaire → aucun bouton de recyclage.
- [ ] « Recycler 1 » puis « Annuler » → rien ne change.
- [ ] « Recycler 1 » puis « OK » → quantité −1, message « +1 pièce(s) », solde +1 sur l'Accueil.
- [ ] « Recycler les N doublons » → il reste 1 exemplaire, boutons disparus.
- [ ] Dépasser 50 pièces dans la journée → « Plafond quotidien : il reste X pièce(s). », rien n'est retiré.
- [ ] Avec plus de 50 titres différents → « Afficher plus » ajoute la suite.

## 4. Points de vigilance
- **Risques** : le recyclage est définitif. Le JavaScript n'a pas de test automatique.
- **Dette technique** : la recherche parcourt la collection sans index (sans effet à cette échelle). « Afficher plus » pagine par position : un titre ajouté entre-temps ailleurs pourrait décaler la liste.
- **Axes d'amélioration** : ignorer les accents ; filtre « doublons seulement » ; voir le plafond restant avant de recycler. Le catalogue d'essai (100 premières lignes) est peu varié : un tirage au hasard de 100 titres serait plus représentatif.
- **Questions ouvertes** : plafond de recyclage (50) toujours non décidé.

## 5. Tests
- Couverts : recherche (3 champs, casse, accents, `%` et `_`, aucun résultat, collection d'autrui), paramètre `q` de l'API. Parcours vérifié par script dans Chromium : liste, pagination, recherche, confirmation refusée/acceptée, recyclage, plafond, pas de défilement horizontal.
- `ruff check .` : ✅ · `pytest` : ✅ (125 tests)
