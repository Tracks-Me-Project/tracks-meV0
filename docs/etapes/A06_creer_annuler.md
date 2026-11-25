# Étape A06 : créer et annuler une enchère

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a06-creer-annuler` · **PR** : #16

## 1. Résumé fonctionnel
Depuis la Collection, chaque titre propose « Mettre aux enchères » : on choisit le prix de départ et la durée, on confirme, et on arrive sur le détail de la vente. Le titre quitte la collection pendant la vente. Le vendeur peut « Annuler la vente » pendant la première moitié de la durée, tant que personne n'a enchéri ; le temps restant pour annuler est affiché. Les refus sont expliqués en clair.

## 2. Résumé technique
- `src/tracks/auctions.py` : `cancel_deadline` extrait de `cancel` (la règle n'est écrite qu'une fois).
- `src/tracks/api/auctions.py` : la réponse gagne `cancel_seconds_left` (0 si une mise existe ou si le délai est passé).
- `web/app.js` : formulaire dans un volet natif `<details>`, minimum et durées lus dans `/rules`, confirmation, table des refus en français.
- Règle confirmée : pas d'annulation après la première mise (`CLAUDE.md` complété).
- **Écartés** : écran « Nouvelle vente » séparé ; recalculer le délai d'annulation dans la page.

## 3. Guide de recette
Préparation : mode essai (voir `CLAUDE.md`), un joueur avec quelques boosters ouverts.

- [ ] Collection → « Mettre aux enchères » → minimum 10, durées 1, 2, 5, 10, 30 min.
- [ ] Prix 5 → le formulaire refuse (rien n'est envoyé).
- [ ] Vendre à 100 pendant 2 min, « Annuler » dans la confirmation → rien ne change.
- [ ] Confirmer → détail « Ton enchère », « Annulable encore » ≈ 1 min ; le titre a quitté la collection (ou sa quantité a baissé de 1).
- [ ] « Annuler la vente » puis OK → « Annulée par le vendeur », titre revenu dans la collection.
- [ ] Attendre la moitié de la durée → le bouton disparaît seul.
- [ ] Depuis un second onglet (autre joueur), miser via `/docs`, puis annuler → « Annulation impossible : quelqu'un a déjà misé. »
- [ ] Sixième vente ouverte → « Tu as déjà le maximum d'enchères ouvertes. »

## 4. Points de vigilance
- **Risques** : le JavaScript n'a pas de test automatique.
- **Dette technique** : un formulaire de vente rempli est perdu si la liste est rechargée (recherche).
- **Axes d'amélioration** : vue « mes ventes » ; durée proposée par défaut.
- **Questions ouvertes** : la synthèse pour l'associé cite l'annulation après une mise parmi les décisions à prendre ; la décision est désormais prise pour l'alpha (refusée).

## 5. Tests
- Couverts : `cancel_deadline`, `cancel_seconds_left` (ouvert, après une mise, délai passé), refus d'annulation existants. Parcours vérifié par script dans Chromium : création, confirmation, annulation, mise reçue entre-temps, délai passé, limite de 5, prix trop bas.
- `ruff check .` : ✅ · `pytest` : ✅ (128 tests)
