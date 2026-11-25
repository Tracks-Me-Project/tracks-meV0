# Tester l'alpha : mode d'emploi

Le jeu tourne **sur un seul ordinateur**. La partie 1 (installation) est à faire par la personne qui développe ; la partie 2 (jouer) est ouverte à tous.

---

## Partie 1. Installation et lancement (technique)

### Une seule fois
```bash
docker compose up -d
source .venv/bin/activate
docker compose exec db createdb -U tracks tracks_essai          # inutile si la base existe déjà
head -101 data/catalogue.csv > data/catalogue.essai.csv         # 100 titres : des doublons arrivent vite
```

### Dans chaque terminal, d'abord
```bash
cd tracks-meV0 && source .venv/bin/activate
export TRACKS_DATABASE_URL=postgresql+psycopg://tracks:tracks@localhost:5442/tracks_essai
export TRACKS_RULES_PATH=config/rules.essai.toml
```

### Terminal 1 : le jeu
```bash
docker compose up -d
alembic upgrade head && python -m tracks.catalogue data/catalogue.essai.csv
uvicorn tracks.main:app --port 8001
```
Le jeu est à l'adresse **http://localhost:8001/app/**.

### Terminal 2 : les joueurs virtuels
```bash
python -m tracks.simulation.live --bots 5 --every 5    # Ctrl+C pour les arrêter
```
`--bots` : leur nombre ; `--every` : secondes entre deux tours (plus petit = plus nerveux).

### Terminal 3 : après (ou pendant) une partie, le contrôle des comptes
```bash
python -m tracks.simulation.checks
```
« OK » : les soldes correspondent au journal, aucune monnaie n'est apparue ni disparue anormalement et les enchères terminées sont réglées. « ÉCHEC » : noter le message. Le serveur doit être lancé (c'est lui qui règle les enchères). Le nombre de titres n'est pas contrôlé.

### Repartir de zéro
Arrêter le jeu et les joueurs virtuels, puis :
```bash
docker compose exec db dropdb -U tracks tracks_essai
docker compose exec db createdb -U tracks tracks_essai
```
et relancer le terminal 1.

---

## Partie 2. Jouer (environ 15 minutes)

Tout va plus vite que dans le vrai jeu : les ventes durent de 1 à 30 minutes et un nouveau paquet de titres arrive chaque minute. Toutes les autres règles sont les vraies.

**Bon à savoir**
- Chaque onglet du navigateur est un joueur différent. **Fermer l'onglet, c'est perdre ce joueur.**
- Pour jouer à plusieurs : ouvrir plusieurs onglets, un pseudo chacun.
- Les joueurs virtuels se reconnaissent à leur nom (`collectionneur-…`, `parieur-…`, `vendeur-…`). Ils jouent au hasard : ne pas juger l'équilibre du jeu sur eux.

### Le parcours
1. **Arriver** (1 min). Choisir un pseudo. On reçoit 1000 pièces.
2. **Ouvrir des paquets** (2 min). Onglet « Boosters » : en ouvrir plusieurs. Attendre une minute et voir le stock remonter.
3. **Faire le tri** (2 min). Onglet « Collection » : chercher un titre, puis échanger un titre en double contre des pièces.
4. **Vendre** (2 min). Sur un titre : « Mettre aux enchères », prix 20, durée 5 minutes. Regarder si les joueurs virtuels misent.
5. **Enchérir** (3 min). Onglet « Enchères » : miser sur la vente d'un autre. Rester sur la page : si quelqu'un passe devant, un message le dit et les pièces reviennent.
6. **Parier** (3 min). Sur une autre vente, encore dans sa première moitié : deviner son prix final. On ne peut pas à la fois miser et parier sur la même vente.
7. **Voir le résultat** (2 min). Onglet « Paris » : gain ou perte. Onglet « Accueil » : le solde.

### Ce qu'il est intéressant de regarder
- Comprend-on quoi faire sans explication ? Où a-t-on hésité ?
- Les durées, les montants, la mise d'un pari paraissent-ils justes ?
- A-t-on envie de revenir voir une vente ? De parier ?
- Les messages de refus sont-ils clairs ?

### Noter un problème
Pour chaque problème, écrire :
- **ce que je faisais** (écran et boutons) ;
- **ce que j'attendais** ;
- **ce qui s'est passé** (recopier le message, ou faire une capture d'écran) ;
- **l'heure** et le pseudo utilisé.
