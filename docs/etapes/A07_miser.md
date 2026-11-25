# Étape A07 : miser

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a07-miser` · **PR** : PRNUM

## 1. Résumé fonctionnel
Sur le détail d'une enchère ouverte, on voit son solde disponible, on saisit une mise (préremplie au minimum), on confirme. La somme est bloquée tant qu'on mène, rendue si quelqu'un surenchérit, retirée si on gagne. Le vendeur et le meneur ne voient pas le formulaire. Les refus sont expliqués en clair.

## 2. Résumé technique
- `web/app.js` : formulaire de mise, confirmation, 5 refus traduits, écran rechargé après chaque mise ou refus.
- Aucun changement serveur : `POST /auctions/{id}/bids` et les règles existaient.
- **Écartés** : miser en un seul toucher ; bloquer dans la page un solde insuffisant (règle écrite deux fois) ; alerte « tu as été dépassé » (attend A09).

## 3. Guide de recette
Préparation : mode essai, deux onglets (deux joueurs). L'un vend un titre pour 100 pendant 5 min, l'autre ouvre l'enchère.

- [ ] Acheteur : « Ta mise (minimum 100, disponible 1000) ». Vendeur : pas de formulaire.
- [ ] « Miser » puis « Annuler » → rien ne change.
- [ ] Saisir 50 → le formulaire refuse (rien n'est envoyé).
- [ ] Miser 100 → « Tu es en tête », plus de formulaire ; Accueil : Disponible 900, Bloqué 100.
- [ ] 3e onglet : miser 105 → le 2e joueur retrouve 1000 disponible et 0 bloqué (après réouverture).
- [ ] Sans recharger un écran périmé, miser sous le nouveau minimum → « Mise trop basse : le minimum est maintenant … », champ mis à jour.
- [ ] Miser plus que son solde → « Solde disponible insuffisant. »
- [ ] Fin de l'enchère → gagnant : « Tu as remporté cette enchère », titre dans sa collection, solde débité ; vendeur crédité du même montant.

## 4. Points de vigilance
- **Risques** : on peut miser à la dernière seconde (aucune prolongation, ni dans les documents ni dans le code) : à observer pendant l'alpha. La confirmation prend du temps en toute fin d'enchère.
- **Dette technique** : le JavaScript n'a pas de test automatique.
- **Axes d'amélioration** : alerte « tu as été dépassé » ; vue « mes mises en cours » ; montant bloqué visible sur l'écran d'enchère.
- **Questions ouvertes** : faut-il une prolongation en cas de mise tardive ?

## 5. Tests
- Couverts : règles de mise (tests existants du domaine et de l'API). Parcours vérifié par script dans Chromium : confirmation refusée, mise, solde bloqué puis rendu, mise trop basse, solde insuffisant, gain, soldes finaux.
- `ruff check .` : ✅ · `pytest` : ✅ (128 tests)
