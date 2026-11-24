# Où en est le premier prototype : synthèse pour décider

*Document du 24 novembre 2026. Il résume ce qui fonctionne aujourd'hui, ce que les tests montrent
et ce qu'il reste à trancher. Aucune connaissance technique n'est nécessaire.*

## 1. En deux phrases
Le cœur du jeu fonctionne : on ouvre des boosters, on collectionne des titres, on les met aux
enchères, on enchérit et on parie sur le prix final. Il n'y a pas encore d'écran : tout se pilote
par programme, ce qui nous a permis de le tester à fond avant d'y construire quoi que ce soit
dessus.

## 2. Ce qu'un joueur peut faire aujourd'hui

| Action | Comment ça marche |
|---|---|
| **Créer un compte** | Il reçoit **1 000 de monnaie** et 10 boosters. |
| **Ouvrir un booster** | 5 titres tirés au hasard parmi **20 270 titres**. Un nouveau booster arrive chaque heure, avec 10 en réserve au maximum. On ne peut pas en acheter. |
| **Recycler un doublon** | Un titre en double rendu au jeu rapporte 1 de monnaie, dans la limite de **50 par jour**. On garde toujours un exemplaire de chaque titre. |
| **Mettre un titre aux enchères** | Durée au choix : 30 min, 1 h, 3 h, 6 h ou 12 h. Le vendeur fixe le prix de départ (10 au minimum). 5 enchères en vente en même temps au maximum. **Pas de frais, pas de commission** : le vendeur touche exactement le prix final. |
| **Enchérir** | Chaque offre dépasse la précédente d'au moins 5 %. La monnaie de l'offre est mise de côté. Elle est rendue si quelqu'un surenchérit, et retirée si on gagne. |
| **Annuler une vente** | Possible pendant la première moitié de la durée, tant que personne n'a enchéri. |
| **Parier sur le prix final** | Le joueur devine à quel prix l'enchère se terminera. La mise est toujours **10 % du prix de départ**. On peut parier pendant la première moitié de la durée, sur 3 enchères en même temps au maximum. |

**Comment les paris sont partagés.** Les trois pronostics les plus proches du prix final se partagent
l'essentiel de la cagnotte (50 %, 30 %, 20 %), les autres parieurs se partagent le reste. Un gain ne
dépasse jamais 4 fois la mise. Un parieur seul est remboursé, et tout le monde est remboursé si
l'enchère est annulée ou si personne n'a enchéri.

*Exemple.* Six joueurs parient 20 chacun sur une enchère qui finit à 580. Le plus proche gagne 48
(+28), le deuxième 28 (+8), le troisième 19 (-1) et les trois autres reçoivent 8 (-12).

**Interdits :** parier sur sa propre enchère, et enchérir **et** parier sur la même enchère.
Les pronostics des autres joueurs restent cachés.

## 3. Ce que nous avons vérifié

**Une simulation avec 20 joueurs virtuels pendant 3 jours** (jeu entier, sans intervention) :

| Mesure | Résultat |
|---|---|
| Boosters ouverts | 1 552 |
| Enchères mises en vente | 504 |
| Enchères vendues | 258, soit **51 %** |
| Enchères sans acheteur | 218 |
| Paris réglés | 162 : 64 gagnants, 98 perdants |
| Gain moyen d'un parieur | **-3,2 %** de sa mise (l'étude précédente donnait -3,4 %) |
| Monnaie détruite par les paris | 64 (arrondis et plafond des gains) |
| Incident serveur | **aucun** |

À la fin de chaque simulation, nous vérifions que **la monnaie et les titres se retrouvent
exactement** : rien n'est créé ni perdu par erreur, et chaque enchère ou pari terminé est bien réglé.

**Des tentatives de triche simples**, lancées au même instant pour profiter d'un défaut :
- dépenser deux fois la même monnaie (par exemple miser 5 fois 400 avec 1 000 en poche) : **bloqué** ;
- ouvrir plus de boosters que le stock, recycler au-delà du plafond, dépasser les 5 ventes ou les
  3 paris en même temps : **bloqué** ;
- parier et enchérir ensemble sur la même enchère, annuler une vente pendant qu'on enchérit : **bloqué** ;
- agir avec un faux compte ou au nom d'un autre joueur : **refusé**.

Ces essais ont aussi fait apparaître **cinq défauts**, aujourd'hui corrigés : des chiffres
absurdes (un prix de plusieurs milliards, un caractère interdit dans un nom) faisaient planter le
serveur au lieu d'être refusés poliment.

## 4. Ce qu'il faut lire avec prudence
- **Les 51 % d'enchères vendues ne sont pas un résultat de jeu.** Nos joueurs virtuels fixent leurs
  prix au hasard. L'étude précédente parlait de trois enchères sur quatre : nous ne savons pas encore
  comment de vrais joueurs se comporteront.
- Les joueurs virtuels sont simples et ne trichent pas en groupe. La simulation montre que le jeu
  tient techniquement, pas qu'il est amusant ni équilibré.
- Très peu de doublons apparaissent avec 20 270 titres : le recyclage n'a rapporté que 102 sur
  3 jours. Il faudra le surveiller avec de vrais joueurs.

## 5. Risques connus et acceptés
- **Pas de commission : la monnaie ne fait que grossir.** Presque rien ne la retire du jeu (seulement
  les arrondis des paris). L'étude montrait déjà que les prix finissent par monter.
- **Entente entre comptes complices.** Sans commission, trois à cinq comptes qui s'entendent peuvent
  gagner de l'argent sur les paris. Nous n'avons pas de détection de tricheurs, ce qui était prévu.
- **Une seule personne peut créer plusieurs comptes** : il n'y a ni mot de passe ni vérification.

## 6. Décisions à prendre
1. **Plafond de recyclage** : 50 par jour aujourd'hui (valeur de travail, jamais tranchée).
2. **Monnaie de départ** : 1 000. C'est la valeur de la simulation, pas une règle des documents.
3. **Prix de départ minimum** : 10. Nous l'avons choisi pour qu'une mise de pari ne soit jamais nulle.
4. **Stock de boosters d'un nouveau joueur** : 10 d'emblée, pour qu'il puisse jouer tout de suite.
5. **Annulation d'une vente** : refusée dès la première offre, comme dans la simulation. Les
   documents ne le disaient pas.
6. **Heure de remise à zéro du plafond de recyclage** : minuit en temps universel, soit 1 h ou 2 h du
   matin en France. Acceptable ?
7. **Commission sur les ventes** : toujours à décider (4 à 5 % recommandés par l'étude précédente).
8. **Aide aux nouveaux joueurs** et **moyen de retirer de la monnaie** : sujets ouverts depuis le
   résumé des règles de base.

## 7. Ce qui n'existe pas encore
Quêtes quotidiennes, haut-faits, souhaits et jauge chaud/froid, boosters orientés vers les goûts du
joueur, détection de tricheurs, mot de passe et vérification des comptes, et **toute interface**
(écrans, application). Le tirage des boosters est uniforme.

## 8. Point juridique à ne pas oublier
Les paris avec de la monnaie de jeu (mises, gains) doivent être **vérifiés par un juriste avant toute
mise en ligne**. À ce jour nous n'avons pas confirmé que cette vérification est lancée.
