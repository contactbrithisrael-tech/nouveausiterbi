# Le serveur de l'Atelier, et ses épreuves

Le programme de gestion (`secretariat.html`) parle à cinq fonctions
Cloudflare Pages, dans `functions/api/`, qui écrivent dans une base D1.

| Fonction | Ce qu'elle fait |
|---|---|
| `entrer.js` | ouvre une session sur un mot de passe |
| `sortir.js` | la ferme, et efface le biscuit |
| `etat.js`   | lit et écrit le registre partagé de l'Atelier |
| `porte.js`  | dit si le serveur a de quoi reconnaître quelqu'un |
| `mdp.js`    | change le mot de passe de qui est connecté |

`001-socle-en-ligne.sql` est le schéma à passer dans la console D1.
Les comptes s'ajoutent à la main, un `INSERT` par Officier.

## Rejouer les épreuves

Tout se lit dans le dépôt : aucun fichier privé, aucun chemin absolu,
aucun vrai mot de passe. Les comptes, la page et le tableau d'épreuve
sont inventés.

```sh
node loge/serveur/essai-api.mjs          # le serveur seul, sur SQLite

node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
export RBI_PAGE=/tmp/page-epreuve.html

RBI_PORT=8787 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8788 RBI_SANS_COMPTES=1 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8789 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8790 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8791 RBI_SANS_COMPTES=1 node loge/serveur/faux-serveur.mjs &

RBI_URL=http://127.0.0.1:8787/ python3 loge/serveur/essai-documents.py
RBI_URL=http://127.0.0.1:8789/ python3 loge/serveur/essai-partage.py
RBI_URL_SANS=http://127.0.0.1:8788/ RBI_URL_AVEC=http://127.0.0.1:8789/ \
  python3 loge/serveur/essai-verrou.py
RBI_URL_AVEC=http://127.0.0.1:8790/ RBI_URL_SANS=http://127.0.0.1:8791/ \
  python3 loge/serveur/essai-mdp.py
```

**Chaque suite veut un serveur neuf.** La base est en mémoire : une
suite qui change un mot de passe ou écrit le registre laisse le serveur
dans un état où la suivante ne se reconnaît plus. D'où les cinq ports.

`RBI_SANS_COMPTES=1` démarre un serveur dont la table des utilisateurs
est vide — la panne du premier soir, celle où le serveur refusait tout
le monde.

## Ce que chaque suite éprouve

- **`essai-api.mjs`** — les fonctions seules, contre un vrai SQLite :
  empreintes salées, jetons, sessions, concurrence par version, journal,
  changement de mot de passe.
- **`essai-partage.py`** — deux Officiers sur deux appareils : ce que
  l'un saisit, l'autre le voit ; une écriture périmée est refusée.
- **`essai-verrou.py`** — un serveur mal réglé n'enferme personne
  dehors ; le lien au registre survit à un rechargement ; une session
  expirée referme la porte au lieu de laisser croire au partage.
- **`essai-mdp.py`** — chacun change son mot de passe, et **l'ancien
  ne rouvre plus** malgré l'empreinte restée dans la page.
- **`essai-documents.py`** — la qualité et le contreseing du Souverain
  Grand Commandeur sur chaque document, la feuille des Visiteurs sur sa
  page, le point du Temple sur la convocation.

## Ce qui ne doit jamais entrer ici

Le dépôt est **public**, et Cloudflare Pages sert tout ce qu'il porte.
Aucun nom de Sœur ou de Frère, aucune adresse, aucun mot de passe,
aucune empreinte d'un compte réel — pas même dans un commentaire, pas
même « le temps d'une épreuve ».
