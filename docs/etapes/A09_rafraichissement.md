# Étape A09 : rafraîchissement automatique

- **Statut** : ✅ terminé le 2026-11-25
- **Branche** : `a09-rafraichissement` · **PR** : #19

## 1. Résumé fonctionnel
L'accueil, la liste et le détail des enchères et les paris se mettent à jour seuls, toutes les 3 secondes : on voit les surenchères, les nouvelles ventes et les résultats sans recharger. Une saisie en cours n'est pas effacée. Si on perd la tête d'une enchère dont le détail est ouvert, on est prévenu : « Tu as été dépassé ».

## 2. Résumé technique
- `config/rules*.toml`, `config.py` : section `[interface] refresh_seconds = 3` (strictement positif), lue par la page via `/rules`.
- `web/app.js` : boucle unique (la requête suivante part après la réponse, rien quand l'onglet est caché ou pendant une action) ; l'écran n'est redessiné que si les données ont changé ; la saisie et le curseur sont conservés ; un montant devenu trop faible est remplacé par le nouveau minimum ; réponses périmées ignorées.
- Corrige le défaut noté en A08 (saisie effacée quand un délai expire).
- **Écartés** : SSE (le serveur pousse les nouveautés) ; mise à jour champ par champ ; rafraîchir Collection et Boosters (formulaires et décompte propre).

## 3. Guide de recette
Préparation : mode essai, deux onglets côte à côte (il faut qu'ils soient visibles tous les deux).

- [ ] Onglet B sur « Enchères », onglet A met en vente → elle apparaît dans B en moins de 5 s.
- [ ] B ouvre le détail et tape 150 sans valider ; A (ou un 3e joueur) mise 120 → prix à jour, 150 toujours saisi, curseur dans le champ.
- [ ] Une mise à 200 arrive → le champ passe au nouveau minimum (210).
- [ ] B mise, puis un autre surenchérit → « Tu as été dépassé : ta mise t'est rendue. »
- [ ] Accueil et Paris : soldes et paris à jour sans toucher à rien.
- [ ] Arrêter le serveur → « Serveur injoignable » ; le relancer → le message disparaît.
- [ ] Passer sur un autre onglet puis revenir → mise à jour immédiate.
- [ ] Sur téléphone : le clavier ne se ferme pas quand le détail change pendant la saisie.

## 4. Points de vigilance
- **Risques** : chaque lecture d'un détail verrouille brièvement l'enchère (règlement à la lecture) et la liste coûte jusqu'à 8 requêtes par enchère : à revoir avant un hébergement. Une surenchère peut arriver entre deux mises à jour (le serveur refuse alors la mise).
- **Dette technique** : si le serveur est injoignable au premier chargement de la page, il faut la recharger. Pas de test automatique du JavaScript, qui grossit (environ 600 lignes) : envisager de le découper.
- **Axes d'amélioration** : SSE ; alerte de dépassement aussi hors du détail.
- **Non vérifié** : clavier sur un vrai téléphone, retour sur un onglet caché.

## 5. Tests
- Couverts : intervalle positif, présent dans `/rules`. Parcours vérifié par script dans Chromium sans rechargement : liste, saisie conservée, remplacement par le minimum, alerte, accueil, paris, annulation, serveur arrêté puis relancé.
- `ruff check .` : ✅ · `pytest` : ✅ (131 tests)
