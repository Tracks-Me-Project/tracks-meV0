# Étape A08 : paris

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a08-paris` · **PR** : PRNUM

## 1. Résumé fonctionnel
Sur le détail d'une enchère, on peut parier sur son prix final : mise fixe affichée, temps restant pour parier, confirmation. Quand on ne peut pas parier (sa propre vente, déjà enchéri, déjà parié, paris fermés), la raison est écrite à la place du formulaire. Après un pari, on ne peut plus enchérir sur cette vente, et c'est dit avant de confirmer. L'onglet « Paris » montre ses paris en cours et terminés (prix final, gain, résultat net) et explique le partage de la cagnotte. Ni le nombre de parieurs ni la cagnotte ne sont affichés avant la fin.

## 2. Résumé technique
- `src/tracks/auctions.py` : `bets_close_at` (la règle de clôture n'était écrite qu'en double).
- `src/tracks/api/auctions.py` : le détail gagne `bets_seconds_left`, `my_prediction`, `i_have_bid` (propres au joueur) ; `GET /bets` gagne `title`, `artist`, `seconds_left`.
- `web/` : section pari du détail, écran `#bets`, 6 refus traduits, textes des règles construits depuis `/rules`, 5 onglets.
- **Écartés** : déduire l'état du joueur de `GET /bets` (paginé, ignore les mises) ; écran de pari séparé.

## 3. Guide de recette
Préparation : mode essai, trois onglets au moins (vendeur et deux parieurs ou plus). Vendre un titre à 100 pendant 2 min : les paris ferment au bout d'1 min.

- [ ] Onglet « Paris » sans pari → message d'aide ; « Comment ça marche » donne les chiffres.
- [ ] Vendeur, sur sa vente → « C'est ta vente : tu ne peux pas parier dessus. »
- [ ] Parieur : « Paris ouverts encore … », mise 10 ; parier 130 → solde disponible −10, bloqué +10, « Tu as parié 130 », plus de formulaire de mise.
- [ ] Un joueur qui a enchéri → « Tu as enchéri : tu ne peux pas parier sur cette enchère. »
- [ ] Un autre joueur n'a aucun moyen de voir le pronostic.
- [ ] Après la moitié de la durée → « Les paris sont fermés pour cette enchère. »
- [ ] Parier sous un prix qui vient de monter → « Pronostic trop bas : le prix a déjà atteint … ».
- [ ] 4e pari en cours → « Tu as déjà le maximum de paris en cours. »
- [ ] À la fin (vente) → onglet Paris, « Terminés » : prix final, gain, net ; soldes à jour. Exemple à 3 parieurs de mise 10 : 15 / 9 / 6.
- [ ] Parieur seul, vente annulée ou invendue → mise remboursée.

## 4. Points de vigilance
- **Risques** : **faire vérifier les paris par un juriste avant toute ouverture à des tiers.** Entente entre comptes complices non détectée (hors périmètre).
- **Dette technique** : quand un délai affiché atteint zéro (clôture des paris, fin d'annulation), l'écran se recharge et efface une saisie en cours. L'onglet Paris montre les 50 derniers paris. Jusqu'à 8 requêtes en base par enchère listée.
- **Axes d'amélioration** : montrer le rang obtenu et le nombre de parieurs une fois la vente terminée.
- **Questions ouvertes** : aucune nouvelle (nombre de parieurs et cagnotte masqués : décidé).

## 5. Tests
- Couverts : `bets_close_at`, champs propres au joueur, pronostic jamais visible par autrui, liste des paris avant et après règlement (le partage du podium était déjà testé). Parcours vérifié par script dans Chromium : pari, interdits, pronostic trop bas, fermeture, résultat à 3 parieurs.
- Non vérifiés à l'écran : limite de 3 paris, annulation et invendu avec paris (couverts côté serveur).
- `ruff check .` : ✅ · `pytest` : ✅ (130 tests)
