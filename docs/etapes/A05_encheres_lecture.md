# Étape A05 : enchères en lecture

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a05-encheres-lecture` · **PR** : PRNUM

## 1. Résumé fonctionnel
Un onglet « Enchères » liste les enchères ouvertes (la plus proche de sa fin en premier) avec prix, nombre de mises et temps restant. Un toucher ouvre le détail : vendeur, prix, mise minimale suivante, meneur, et « Ton enchère » ou « Tu es en tête ». À la fin du décompte, le résultat s'affiche (vendue à qui et combien, invendue ou annulée). On ne peut pas encore créer ni miser depuis la page (A06, A07).

## 2. Résumé technique
- `src/tracks/api/auctions.py` : la réponse gagne `seconds_left` (calculé par le serveur, arrondi au-dessus), `album`, `seller_name`, `leader_id`, `leader_name`, `winner_name`. Pseudos visibles : décision prise pour l'alpha. Les pronostics des paris restent cachés.
- `web/app.js` : écrans `#auctions` et `#auction/<id>` ; un seul décompte, calculé d'après une échéance ; réponses arrivées après un changement d'écran ignorées (corrige aussi la dette notée en A03).
- **Écartés** : calculer le temps restant avec l'horloge du téléphone ; rafraîchissement continu (A09) ; pagination (50 enchères au plus affichées).

## 3. Guide de recette
Préparation : mode essai (voir `CLAUDE.md`). Pour créer une enchère sans A06, ouvrir http://localhost:8001/docs :
1. `POST /accounts` avec `{"name": "vendeur"}` → copier `token`, puis bouton **Authorize** et le coller.
2. `POST /boosters/open` → copier un `id` de titre.
3. `POST /auctions` avec `{"recording_mbid": "<id>", "start_price": 100, "duration_minutes": 2}`.

- [ ] Sans enchère : onglet « Enchères » → « Aucune enchère ouverte. »
- [ ] Après création (changer d'onglet pour rafraîchir) → l'enchère est listée, le temps descend.
- [ ] Toucher l'enchère → détail : vendeur, prix de départ 100, mise minimale 100, meneur « personne ». « ← Enchères » revient à la liste.
- [ ] Dans `/docs`, avec le jeton du joueur de la page (ou un 3e joueur), `POST /auctions/{id}/bids` `{"amount": 100}` puis rouvrir le détail → mise minimale 105, meneur affiché, « Tu es en tête » pour ce joueur.
- [ ] Laisser le décompte finir sur le détail → « Vendue à … pour … » sans recharger. Sans aucune mise → « Terminée sans mise : invendue ».
- [ ] L'enchère finie a disparu de la liste.
- [ ] `POST /auctions/{id}/cancel` (jeton du vendeur) → détail « Annulée par le vendeur » après réouverture.
- [ ] Adresse `#auction/9999` → « Enchère introuvable. »

## 4. Points de vigilance
- **Risques** : le JavaScript n'a pas de test automatique.
- **Dette technique** : jusqu'à 6 requêtes en base par enchère listée ; les mises des autres n'apparaissent qu'en rouvrant l'écran (A09).
- **Axes d'amélioration** : écran « mes enchères terminées » (aujourd'hui le résultat n'est visible que sur le détail).
- **Questions ouvertes** : visibilité des pseudos à confirmer avant ouverture à des tiers.

## 5. Tests
- Couverts : nouveaux champs avant et après mise, arrondi du temps restant, gagnant après la fin. Parcours vérifié par script dans Chromium : liste vide, liste, détail, surenchère, fin avec vente, annulation, enchère inconnue.
- `ruff check .` : ✅ · `pytest` : ✅ (126 tests)
