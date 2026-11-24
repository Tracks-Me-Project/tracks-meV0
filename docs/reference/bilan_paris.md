# Bilan : le système de paris (mise fixe, sans jeton, en podium)

*À destination de l'associé marketing et de l'équipe de développement. Document rédigé le 24
octobre 2026, à partir de la simulation (100 joueurs, 90 jours, 5 simulations par configuration,
catalogue de 10 000 titres, tricheurs programmés). Les chiffres sont des **tendances** : ils servent
à comparer des règles entre elles, pas à prédire ce que feront de vrais joueurs.*

---

## 1. L'essentiel

Nous cherchions un système de paris qui **récompense la prise de risque sans devenir trop
profitable**, et que l'on ne puisse pas exploiter facilement. Voici ce que la simulation montre.

1. **Le partage de la cagnotte « en podium » est meilleur que « le plus proche prend tout ».** Les
   trois plus proches du prix final se partagent la cagnotte (50 / 30 / 20 %). Le meilleur gain
   tombe de ×10 à ×4 la mise et l'entente classique, rentable avec le gagnant unique (+129), perd de l'argent avec le podium (–748).
2. **La mise fixe à 10 % du prix de départ est le bon niveau.** À 5 %, les arrondis grignotent les
   gains (–7 % de rendement) ; à 20 %, les gains sont plus fréquents (38 % de gagnants) mais la
   triche perd moins d'argent.
3. **Le podium ne suffit pas seul à décourager les ententes si l'économie ne prélève rien.** Sans
   commission ni caution, truquer ne coûte presque rien et reste rentable (+400 à +800 par tricheur
   sur 90 jours).
4. **Une commission de 3 à 5 % sur les ventes règle le problème** : l'entente à trois comptes perd
   de l'argent dès 2 %, l'entente à cinq comptes dès 3 à 4 %.
5. **Les autres protections testées (taxe sur les paris, limite d'achats par paire, repérage des
   comptes suspects) n'apportent rien ou coûtent trop cher aux joueurs honnêtes.**

**Réglage recommandé** : mise fixe de 10 %, pas de jeton, 3 paris ouverts au plus, paris fermés à
50 % de la durée, podium 50 / 30 / 20 sur 80 % de la cagnotte (les autres parieurs se partagent le
reste), gain plafonné à 4 fois la mise, commission de 4 à 5 % sur les ventes.

---

## 2. Les paramètres, un par un

« Testé » signifie que nous avons comparé plusieurs valeurs ; « fixé » que nous avons appliqué la
règle décidée sans la comparer à une alternative.

| Paramètre | Valeur retenue | Valeurs comparées | Ce que nous avons constaté | Conclusion |
|---|---|---|---|---|
| **Mise d'un pari** | 10 % du prix de départ, identique pour tous | 5 %, 10 %, 20 % | 5 % : rendement –7 %, 20 % de gagnants. 10 % : –3,4 %, 31 % de gagnants. 20 % : –1,8 %, 38 % de gagnants. | Retenir 10 %. À 5 %, l'arrondi des petites sommes détruit trop de monnaie. |
| **Jeton pour parier** | Aucun | Fixé | Les paris par joueur et par jour restent proches de 0,8 à 0,9. | Retenu. Le plafond de 3 paris ouverts suffit à limiter l'activité. |
| **Paris ouverts en même temps** | 3 par joueur | Fixé | 15 à 18 % des joueurs honnêtes atteignent la limite au moins une fois. | Retenu. À surveiller : un joueur qui parie souvent la ressentira. |
| **Fin des paris** | À 50 % de la durée de l'enchère | Fixé | Les tricheurs visent un prix qu'ils font tomber au dernier moment, après la fermeture. | Retenu. N'empêche pas le trucage : seul le coût de la triche le décourage. |
| **Pari au moins égal au prix atteint** | Oui | Fixé | Aucun refus excessif : les joueurs simulés s'y conforment. | Retenu. Évite les paris absurdes. |
| **Répartition de la cagnotte** | Podium | Gagnant unique, podium | Voir sections 4 et 5. | **Retenir le podium.** |
| **Part du podium** | 80 % de la cagnotte (50 / 30 / 20) | Fixé | Les autres parieurs reçoivent 20 % à parts égales. À 4 parieurs, le 4e ne dépasse jamais le 3e (règle ajoutée). | Retenu. |
| **Deux parieurs seulement** | 70 % / 30 % | Fixé | Cas rare. | Retenu. Un parieur seul est remboursé. |
| **Plafond de gain** | 4 fois la mise | Avec et sans plafond | Presque jamais atteint chez les honnêtes (gain maximal ×3,9 contre ×4,2 sans plafond). Atteint dans 4 % des cagnottes quand les parieurs courent après les grosses cagnottes. | Retenir. Il coûte presque rien et borne le gain en cas d'exploit. |
| **Arrondis** | Gains entiers, reste détruit | Fixé | Environ 3 % des mises sont perdues en arrondis. | Retenu. Légère destruction de monnaie, sans effet notable. |
| **Taxe sur les cagnottes** | 0 % | 0 % et 10 % | Avec 10 % : le gain de l'entente à 5 comptes chute de 80 %, mais les honnêtes perdent 18 à 20 % de leurs mises (contre 7 à 10 %). | Écarter. |
| **Limite d'achats au même vendeur** | Aucune | Aucune, 3 par semaine | Aucun effet sur le gain des tricheurs ; 23 % d'honnêtes freinés (contre 16 %). | Écarter. |
| **Repérage des comptes suspects** | Aucun | Aucun, 3 % par jour | Le profit des tricheurs ne baisse presque pas (–16 % à l'entente à 5 comptes) ; 41 % des honnêtes gelés à tort. | Écarter pour les paris. |
| **Commission sur les ventes** | À décider (4 à 5 % conseillé) | 0, 1, 2, 3, 5 % | Voir section 5. | **Retenir 4 à 5 %** (3 % au minimum). |

---

## 3. Un exemple : une enchère dont le prix de départ est de 200

Six joueurs parient, chacun avec la même mise de **20** (10 % de 200). La cagnotte vaut 120. L'enchère
se termine à **580**.

| Rang | Pari sur le prix final | Écart | Reçoit | Résultat |
|---|---|---|---|---|
| 1er | 600 | 20 | 48 | **+28** |
| 2e | 550 | 30 | 28 | **+8** |
| 3e | 620 | 40 | 19 | **–1** |
| 4e | 450 | 130 | 8 | **–12** |
| 5e | 800 | 220 | 8 | **–12** |
| 6e | 350 | 230 | 8 | **–12** |

Le gagnant gagne 140 % de sa mise, le perdant en perd 60 %. Au moins 1 unité de cagnotte est détruite
par arrondi. Avec 15 parieurs, le premier devrait toucher ×6 sa mise : le plafond le limite à ×4 et
détruit le surplus.

---

## 4. Comparatif : joueurs honnêtes seuls

Quand personne ne triche, que gagne-t-on en pariant ?

| Configuration | Parieurs gagnants | Meilleur gain pour une mise | Rendement moyen | Résultat moyen sur 90 jours |
|---|---|---|---|---|
| **A. Gagnant unique** (le plus proche prend tout) | 46 % | **×10** | 0 % | –0 |
| **B. Podium, plafond ×4 (retenu)** | 31 % | ×3,9 | –3,4 % | –21 |
| C. Podium sans plafond | 32 % | ×4,2 | –3,5 % | –20 |
| D. Podium, mise de 5 % | 20 % | ×4,0 | –7,0 % | –22 |
| E. Podium, mise de 20 % | 38 % | ×4,0 | –1,8 % | –19 |

**Lecture.** Le podium réduit le meilleur gain de ×10 à ×4, ce qui répond à l'objectif « récompenser
le risque sans que ce soit trop profitable ». Il fait aussi passer la part de gagnants de près de la
moitié à un tiers : gagner devient plus rare, mais le joueur moyen ne perd que 3 % de ses mises.

**Conclusions par configuration**

- **A. Gagnant unique** : *à écarter*. Le meilleur gain de ×10 est trop élevé, et c'est le système
  le plus facile à exploiter par entente (section 5).
- **B. Podium avec plafond** : *à retenir*. C'est le meilleur compromis entre gain possible et risque
  de perte limité.
- **C. Podium sans plafond** : *équivalent à B chez les honnêtes*. On garde pourtant le plafond comme
  garde-fou, car il coûte presque rien.
- **D. Mise de 5 %** : *à écarter*. Les arrondis détruisent 7 % des mises, et seuls 20 % des joueurs
  gagnent : expérience décevante.
- **E. Mise de 20 %** : *intéressante pour les honnêtes, mais plus risquée* : les joueurs gagnent
  plus souvent, mais la triche perd moins (–599 contre –748, section 5.1). À revoir si l'on veut un jeu plus
  généreux.

---

## 5. Comparatif : avec des tricheurs

Nous avons fait jouer 8 tricheurs dans la population. Le **profit réel** est ce qu'un tricheur gagne
au final avec ses paris truqués, coûts déduits (positif : il gagne de l'argent, aux dépens des
parieurs honnêtes).

Trois tricheries ont été testées :
- **Entente à trois comptes** : un compte met l'enchère en vente, un autre parie sur un prix, un
  troisième enchérit au dernier moment pour faire tomber le prix pile.
- **Entente à cinq comptes** : même chose, mais deux comptes de plus parient autour du prix visé
  (±2 %) pour occuper tout le podium.
- **Parieurs attirés par les grosses cagnottes** : les joueurs honnêtes parient plutôt sur les
  grosses cagnottes, ce qui profite aux tricheurs.

### 5.1 Économie actuelle (commission de 5 %, caution de 10 %)

| Tricherie | Gagnant unique | Podium |
|---|---|---|
| Entente à trois comptes | **+129** | **–748** |
| Entente à cinq comptes | +98 | **–591** |
| Parieurs attirés par les grosses cagnottes | **+4 480** | **+427** |
| Rendement des honnêtes (entente à trois comptes) | –12,6 % | –7,2 % |

Effet de la mise fixe sur l'entente à trois comptes avec le podium : 5 % → **–865**, 10 % → **–748**,
20 % → **–599**. Plus la mise est grosse, plus la cagnotte à voler est grosse, mais la triche perd
encore dans les trois cas.

**Conclusions.** Le podium fait **perdre de l'argent** à l'entente classique et à celle à cinq
comptes, parce que les mises supplémentaires coûtent plus que ce qu'elles rapportent. Il n'élimine
pas la triche quand les joueurs courent après les grosses cagnottes (+427), mais la divise par dix.
Les honnêtes perdent moitié moins à cause des tricheurs.

### 5.2 Économie sans commission ni caution

| Tricherie | Gagnant unique | Podium |
|---|---|---|
| Entente à trois comptes | **+1 524** | **+417** |
| Entente à cinq comptes | **+1 712** | **+790** |
| Rendement des honnêtes (entente à cinq comptes) | –15,3 % | –10,0 % |

**Conclusions.** Quand truquer ne coûte plus rien, **toutes les ententes redeviennent rentables**,
même avec le podium. Le podium réduit le gain de 73 % (trois comptes) et 54 % (cinq comptes), sans
l'éliminer. Les honnêtes perdent environ 30 à 50 de plus par joueur sur 90 jours, soit de l'ordre de
1 % de leur monnaie, mais cela augmente avec le nombre de tricheurs.

### 5.3 Protections ajoutées au podium (sans commission ni caution)

| Protection | Entente à trois comptes | Entente à cinq comptes | Rendement des honnêtes | Honnêtes pénalisés |
|---|---|---|---|---|
| **Aucune** | +417 | +790 | –7 % / –10 % | 16 % freinés |
| Taxe de 10 % sur les cagnottes | +310 | **+153** | **–18 % / –20 %** | 16 % |
| 3 achats par semaine au même vendeur | +454 | +745 | –8 % / –10 % | **23 % freinés** |
| Repérage à 3 % par jour | +493 | +662 | –8 % / –10 % | **41 % gelés à tort** |

**Conclusions par protection**

- **Taxe de 10 %** : *à écarter*. Elle fait baisser le gain du tricheur à cinq comptes de 80 %, mais
  elle pénalise bien plus les honnêtes : ils ne sont plus que 4 % à terminer gagnants.
- **Limite d'achats par paire** : *à écarter pour les paris*. Aucun effet sur le gain, et elle freine
  7 points de joueurs honnêtes en plus. Elle reste utile contre les ventes en rond (étude précédente).
- **Repérage des comptes suspects** : *inefficace ici*. Le gain est encaissé avant le repérage, et la
  protection gèle injustement 41 % des honnêtes. À réserver aux autres abus (fermes à comptes).

### 5.4 Le niveau de commission qui rend la triche perdante

Podium, sans caution :

| Commission | Entente à trois comptes | Entente à cinq comptes | Monnaie détruite pour 1 créée | Monnaie moyenne en fin de partie |
|---|---|---|---|---|
| 0 % | **+417** | **+790** | 0,01 | 5 000 à 5 300 |
| 1 % | +210 | +483 | 0,09 | 4 700 à 5 050 |
| 2 % | **–22** | +220 | 0,18 | 4 400 à 4 800 |
| 3 % | –237 | **+21** | 0,26 | 4 150 à 4 500 |
| 5 % (avec caution) | –748 | –591 | 0,44 | 3 600 à 3 900 |

**Conclusions par niveau**

- **0 %** : *à écarter*. Toutes les ententes sont rentables et la monnaie ne cesse de gonfler.
- **1 %** : *insuffisant*. Les deux ententes gagnent encore.
- **2 %** : *protège contre l'entente classique seulement*. L'entente à cinq comptes gagne encore 220.
- **3 %** : *niveau minimal acceptable*. L'entente classique perd 237 ; celle à cinq comptes est à peu
  près à l'équilibre (+21, dans la marge d'incertitude).
- **4 à 5 %** : *niveau recommandé*. Les deux ententes perdent de l'argent, et l'économie détruit près
  de la moitié de la monnaie qu'elle crée, ce qui limite la croissance de la monnaie.

---

## 6. Ce que le podium ne règle pas

- **Les ventes en rond et les paris en rond** (des comptes complices qui s'achètent des titres pour
  gonfler leurs haut-faits) : le gain d'un tricheur est le même avec ou sans podium (environ 31 000
  sur 90 jours, contre 850 pour un joueur honnête). La parade est de limiter les récompenses des
  haut-faits et d'encadrer les achats entre deux mêmes comptes (étude précédente).
- **La multiplication des comptes** : toujours le danger principal. Aucune règle de paris ne la
  traite ; il faut vérifier les comptes à l'ouverture.
- **Les tricheurs qui s'adaptent** : les nôtres jouent une stratégie fixe.

---

## 7. Réglage recommandé

| Paramètre | Valeur |
|---|---|
| Mise | **Fixe, 10 %** du prix de départ |
| Jeton pour parier | **Aucun** |
| Paris ouverts en même temps | **3** par joueur |
| Fin des paris | **50 %** de la durée de l'enchère |
| Pari au moins égal au prix atteint | **Oui** |
| Cagnotte | **Podium** : 80 % aux trois plus proches (50 / 30 / 20), 20 % aux autres ; 70 / 30 à deux parieurs ; parieur seul remboursé |
| Plafond de gain | **4 fois la mise** (surplus détruit) |
| Commission sur les ventes | **4 à 5 %** (3 % au minimum) |
| Caution de mise en vente | Non nécessaire |
| Taxe sur les paris, limite par paire, repérage | Non retenus pour les paris |

---

## 8. Les décisions à prendre

1. **Commission** : accepter 4 à 5 % (recommandé), ou 3 % comme compromis marketing ? Sans commission,
   la triche reste rentable.
2. **Mise** : 10 % (recommandé) ou 20 % si vous voulez un jeu plus généreux avec plus de gagnants ?
3. **Paris simultanés** : la limite de 3 est-elle acceptable pour les joueurs les plus actifs ?
4. **Pronostics habiles** : voulez-vous une récompense pour les joueurs qui pronostiquent
   régulièrement avec justesse ? La simulation ne sait pas la mesurer.
5. **Vérification juridique** : à lancer avant tout développement des paris (monnaie de jeu, mises,
   gains).

---

## 9. Les limites de cette étude

- **Les joueurs honnêtes simulés pronostiquent tous de la même manière.** Leurs gains relèvent donc
  de la chance. De vrais joueurs habiles gagneront davantage, et pourraient dominer le podium.
- **Les tricheurs ne s'adaptent pas.** Un vrai tricheur testera d'autres combines contre le podium.
- **100 joueurs, 90 jours, catalogue de 10 000 titres** : les effets de masse n'apparaissent pas ;
  un nombre de tricheurs plus grand n'a pas été testé dans cette série.
- **Le jeton et la fermeture à 50 % n'ont pas été comparés individuellement** à d'autres valeurs :
  nous avons appliqué les règles décidées.
- **Les chiffres de la section 5 viennent de scénarios différents** (avec ou sans frais) : comparez
  les tableaux entre eux avec prudence.

---

*Les chiffres viennent de la commande `python main.py comparer` appliquée aux scénarios de la
famille « Paris : mise fixe, sans jeton, podium » (31 scénarios, 5 simulations chacun). Les valeurs
exactes se trouvent dans les fichiers `comparaison.csv` produits par cette commande.*
