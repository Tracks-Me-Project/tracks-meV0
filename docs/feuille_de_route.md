# Feuille de route de l'alpha

Objectif : un **banc d'essai jouable des mécaniques** (boosters, recyclage, enchères, paris), en local, avec une interface rudimentaire pensée mobile. Pas d'audio, pas de pochettes, pas d'hébergement, pas d'authentification réelle.

Chaque étape : une branche, une PR, une fiche dans `docs/etapes/` (créée à la fin de l'étape, dans la même PR). Gabarit : `docs/etapes/_modele.md`.

Statuts : ⬜ à faire · 🟨 en cours · ✅ terminé

## Rappel : le PoC (étapes 0 à 6, serveur seul)

Terminé et fusionné (PR #1 à #7) : squelette, comptes et journal de monnaie, catalogue/boosters/collection, recyclage, enchères, paris au podium, joueurs virtuels et tentatives d'abus. Pas de fiche rétrospective pour l'instant.

## Alpha

| N° | Étape | Livrable visible | Statut | Fiche | PR |
|---|---|---|---|---|---|
| A01 | Configuration de test | Durées d'enchères courtes en mode test | ✅ | [A01](etapes/A01_config_essai.md) | |
| A02 | Socle front | Page mobile, créer un joueur, voir son solde | ⬜ | | |
| A03 | Boosters | Voir son stock, ouvrir un booster | ⬜ | | |
| A04 | Collection et recyclage | Liste des titres, recycler un doublon | ⬜ | | |
| A05 | Enchères en lecture | Liste, détail, compte à rebours | ⬜ | | |
| A06 | Enchères : créer et annuler | Mettre un titre aux enchères | ⬜ | | |
| A07 | Enchères : miser | Surenchérir, mise bloquée puis rendue | ⬜ | | |
| A08 | Paris | Parier, voir ses paris, interdits expliqués | ⬜ | | |
| A09 | Rafraîchissement automatique | Écrans à jour sans recharger | ⬜ | | |
| A10 | Scénario multi-joueurs | Plusieurs joueurs et bots, mode d'emploi | ⬜ | | |
| A11 | Bilan de l'alpha | Synthèse claire pour l'associé | ⬜ | | |

## Décisions de cadrage

- Web uniquement, mais conçu comme un jeu mobile (colonne unique, gros boutons).
- Front en HTML + JavaScript simple servi par FastAPI, sans outil de compilation ni nouvelle dépendance.
- Identité : un jeton par joueur (l'authentification réelle viendra avec l'hébergement).
- Rafraîchissement par interrogation régulière (« polling »), pas de temps réel.
- Tests de durée : fichier de configuration « test » aux durées courtes.
- Paris en monnaie fictive, non achetable. Vérification juridique à faire avant toute ouverture à des tiers.

## Points à surveiller

- Les étapes A03 à A08 supposent que l'API expose tout ce qu'il faut à l'écran : à contrôler à chaque étape.
- Si le JavaScript simple devient ingérable, migrer vers un framework (l'API ne change pas).
