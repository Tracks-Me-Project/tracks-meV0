# Les règles de base du jeu : résumé pour décider

*Document du 21 novembre 2026. Il résume les règles retenues pour le premier prototype et ce que
la simulation en montre. La simulation fait jouer 100 joueurs virtuels pendant 90 jours : elle
donne des **tendances pour comparer des règles**, pas des prévisions de ce que feront de vrais
joueurs.*

## 1. L'idée en deux lignes
Le cœur du jeu, ce sont les **enchères** (on met un titre en vente, les autres enchérissent) et les
**paris** (on parie sur le prix final d'une enchère). Tout le reste (boosters, quêtes, recyclage)
sert à donner aux joueurs de quoi jouer sur ces deux fonctions.

## 2. Les règles retenues

| Sujet | Règle |
|---|---|
| **Enchères** | Durée au choix : 30 min, 1 h, 3 h, 6 h ou 12 h. Chaque mise doit dépasser la précédente d'au moins 5 %. 5 enchères ouvertes en même temps au maximum par joueur. **Pas de frais de mise en vente, pas de commission.** |
| **Paris** | Le joueur pronostique le prix final. La mise est fixe : 10 % du prix de départ. 3 paris ouverts au plus. On ne peut plus parier passé la moitié de la durée de l'enchère. Les **trois pronostics les plus proches** se partagent la cagnotte (50 % / 30 % / 20 % de 80 % de la cagnotte), les autres parieurs se partagent le reste. Un gain ne dépasse jamais 4 fois la mise. Un parieur seul est remboursé. |
| **Popularité** | **Plus de rareté** liée aux écoutes ou aux ventes. La popularité d'un titre vient de ce que font les joueurs : leurs **listes de souhaits** (les titres les plus souhaités montent de niveau) et la **jauge chaud / froid** des enchères (un titre qui se vend beaucoup et bien est « chaud »). |
| **Boosters** | Un joueur reçoit régulièrement des boosters de 5 titres (stock de 10). Environ 30 % des titres d'un booster correspondent aux goûts du joueur (ses albums et artistes), le reste est aléatoire. On ne peut plus acheter de boosters avec la monnaie du jeu. |
| **Quêtes quotidiennes** | 6 quêtes par jour, **50 de monnaie au maximum** : 5 par quête, 10 pour « ouvrir beaucoup de boosters », plus 15 de bonus si les six sont faites. |
| **Recyclage** | Un titre en double rendu au jeu rapporte **1 de monnaie**, dans la limite d'un plafond quotidien (valeur encore à choisir, voir section 5). |

## 3. Ce que montre la simulation du jeu de base

- **Les enchères et les paris font vivre le jeu.** 78 % de ce que gagnent les joueurs vient des
  enchères et des paris, et environ trois enchères sur quatre trouvent preneur.
- **Les paris au podium récompensent le risque sans être trop généreux.** Près de quatre parieurs sur dix
  gagnent, et en moyenne un parieur perd un peu (1,7 % de ses mises). Le meilleur gain possible
  est de 4 fois la mise, contre 10 fois avec la règle « le plus proche prend tout ».
- **La monnaie en circulation ne cesse de grossir.** Elle augmente d'environ 7 % par semaine : un
  joueur moyen finit à 12 000, contre 1 000 au départ. Comme il n'y a ni frais ni commission, **rien
  ne retire de la monnaie du jeu**. À terme, les prix montent et les nouveaux joueurs ont du mal à
  suivre les anciens.
- **Les écarts entre joueurs sont déjà marqués.** Les 10 % les plus riches détiennent 41 % de la
  monnaie. Le quart des joueurs les plus pauvres n'a que 14 % de la moyenne.
- **Le recyclage est la première source de monnaie** (56 % de la monnaie créée), devant les
  haut-faits (25 %) et les quêtes (20 %).

## 4. Le test du plafond de recyclage
Nous avons comparé quatre plafonds quotidiens (monnaie qu'un joueur peut gagner par jour en recyclant).

| Plafond | Monnaie en fin de partie (par joueur) | Croissance de la monnaie par semaine | Part des revenus venant du marché | Part des 10 % les plus riches |
|---|---|---|---|---|
| 100 (règle actuelle) | 12 000 | 7 % | 78 % | 41 % |
| 50 | 9 100 | 5,6 % | non relevé | 46 % |
| 25 | 7 500 | 4,7 % | 88 % | 50 % |
| 10 | 6 400 | 4 % | 90 % | 51 % |

**Lecture.** Baisser le plafond ralentit la hausse de la monnaie et donne plus de poids aux
enchères et aux paris, ce que nous voulons. **Mais cela creuse les écarts** : le recyclage est un
petit revenu régulier pour tous, et les plus modestes en dépendent. Et même au plafond le plus bas,
la monnaie continue de grossir.

## 5. Les décisions à prendre

1. **Le plafond de recyclage.** Nous penchons pour 50 par jour, un compromis entre monnaie maîtrisée
   et joueurs modestes protégés. À trancher.
2. **Un moyen de retirer de la monnaie du jeu.** Sans commission, la monnaie gonfle toujours.
   Pistes : une petite commission sur les seuls paris, des dépenses utiles pour les joueurs
   (boutique, personnalisation). À étudier ensuite.
3. **L'écart entre riches et modestes.** Faut-il une aide pour les nouveaux joueurs (par exemple
   un bonus de départ) ? Aujourd'hui, seulement environ un joueur sur quatre gagne de la monnaie sur
   le marché.
4. **La vérification juridique des paris.** À lancer **avant** tout développement : monnaie de jeu,
   mises, gains.

## 6. Les risques à connaître

- **La triche par entente sur les paris reste rentable sans commission.** Trois à cinq comptes
  complices (l'un met en vente, l'un parie, l'un enchérit au dernier moment) gagnent 400 à 800 par
  tricheur sur 90 jours. Avec une commission de 4 à 5 % sur les ventes, ces ententes perdraient de
  l'argent, mais nous avons choisi de ne pas en mettre pour le premier prototype. Le risque est
  accepté, pas résolu.
- **Les fermes à comptes** (une personne, de nombreux comptes) sont la menace la plus sérieuse
  des études précédentes. Les parades retenues (limite d'enchères ouvertes, détection des comptes
  suspects) ne sont pas encore intégrées au jeu de base.
- **Un titre gonflé par des tricheurs sur les souhaits ne redescend pas.** Un petit groupe de comptes
  peut faire monter le niveau d'un titre précis. À corriger.
- **La jauge « chaud / froid » est peu précise avec peu de joueurs.** Avec 100 joueurs, seuls 2 titres
  sur 1 000 ont assez de ventes pour être jugés. Elle n'aura de sens qu'avec beaucoup plus de joueurs.

## 7. Les limites de l'étude

- **Joueurs virtuels** : ils suivent des règles simples. Les vrais joueurs, surtout les plus malins,
  se comporteront autrement.
- **Petite échelle** : 100 joueurs et un catalogue de 10 000 titres (le vrai fera des millions).
- **Pas de tricheurs dans ces tests de base.** Leur effet a été mesuré dans des études séparées.
- **Chiffres moyens de 5 simulations** : à lire comme des ordres de grandeur.

## 8. Ce qui a été écarté
Rareté fondée sur les écoutes ou les ventes, fusion de titres, jetons de pari, taxe sur les paris,
limite d'achats entre deux mêmes comptes, achat de boosters avec la monnaie du jeu.
