# Règles de base du premier PoC (scénario « socle »)

*Fixées le 21 novembre 2026. Ce sont les règles de départ : chaque future comparaison se fait par
rapport à elles (`python main.py comparer --reference socle`). Les résultats de simulation donnent
des tendances, pas des valeurs définitives.*

## Ce qui est fixé

| Domaine | Règle |
|---|---|
| **Enchères** | Durées de 30 min, 1 h, 3 h, 6 h ou 12 h. Une nouvelle mise dépasse la précédente d'au moins 5 %. **5 enchères ouvertes** au plus par compte. **Aucun frais de mise en vente, aucune commission.** |
| **Paris** | On pronostique le prix final. Mise fixe de **10 %** du prix de départ, 3 paris ouverts au plus, paris fermés à la moitié de la durée de l'enchère, pari au moins égal au prix déjà atteint. Les trois plus proches se partagent 80 % de la cagnotte (50 / 30 / 20), les autres le reste ; le gain est plafonné à 4 fois la mise ; un parieur seul est remboursé. (Détails : `bilan_paris.md`.) |
| **Popularité** | Plus de rareté : la popularité d'un titre vient des **souhaits** des joueurs (niveaux C à L) et de la **jauge chaud/froid** des enchères, calculée sur 14 jours. Un souhait pèse moins quand la liste du joueur est longue (protège contre les scripts). |
| **Boosters** | 1 booster de 5 titres par heure, stock de 10. **30 % des cartes** visent les albums et artistes qui intéressent le joueur ; tirage sinon uniforme. Les packs ne s'achètent plus. |
| **Quêtes** | 6 quêtes par jour : 5 de monnaie pour chacune des cinq premières, 10 pour « ouvrir beaucoup de boosters », plus 15 de bonus si les six sont faites : **50 par jour au maximum**. |
| **Recyclage** | **1 titre recyclé = 1 de monnaie**, dans la limite de 100 par jour. |

## Risque connu : l'absence de commission
Sans commission ni caution, la triche par entente sur les paris reste rentable même avec le podium
(+417 à trois comptes, +790 à cinq par tricheur sur 90 jours, d'après `bilan_paris.md`). La monnaie
détruite est aussi presque nulle : la monnaie en circulation ne cesse de gonfler. Décision du
21 novembre : on accepte ce risque pour le premier PoC et on testera d'autres protections ensuite
(limite d'achats par paire, détection avec bannissement, petite commission sur les paris seuls).

## À recalibrer (valeurs de départ, pas des décisions)
- Plafond de recyclage (100 par jour) : à revoir avec la monnaie créée par les quêtes.
- Récompenses des haut-faits.
- Protections contre les tricheurs des souhaits : la dilution est retenue ; la qualité du compte est
  laissée de côté (elle ne détecte rien, bilans E4 et E8).
- Un titre qui monte de niveau par triche ne redescend jamais (bilan E8) : à traiter.

## Non retenu pour le socle
Rareté par écoutes ou ventes, fusion, jetons de pari, taxe sur les paris, limite d'achats par paire
et repérage des comptes (inefficaces ou trop coûteux pour les honnêtes, voir `bilan_paris.md`).
