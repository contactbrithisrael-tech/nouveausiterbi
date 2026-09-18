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
| `envoyer.js` | remet la convocation par un service de courrier, et en rend compte |
| `_courriel.js` | les deux services possibles — Brevo, Resend |
| `annuaire.js` | reçoit les fiches du formulaire, et les rend à la Secrétaire |
| `reponse.js` | la SEULE route sans session : on y répond avec son seul lien |
| `reponses.js` | relève les réponses pour le Secrétariat — session exigée |

`001-socle-en-ligne.sql` est le schéma à passer dans la console D1,
puis `002-annuaire.sql`, `003-envois.sql` et `004-reponses.sql`. Les
comptes s'ajoutent à la main, un `INSERT` par Officier.

## Rejouer les épreuves

Tout se lit dans le dépôt : aucun fichier privé, aucun chemin absolu,
aucun vrai mot de passe. Les comptes, la page et le tableau d'épreuve
sont inventés.

```sh
node loge/serveur/essai-api.mjs          # le serveur seul, sur SQLite
node loge/serveur/essai-outil-mdp.mjs    # le SQL imprimé ouvre-t-il vraiment ?
node loge/serveur/essai-gps.mjs          # la lecture du point du Temple

node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
export RBI_PAGE=/tmp/page-epreuve.html

RBI_PORT=8787 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8788 RBI_SANS_COMPTES=1 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8789 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8790 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8791 RBI_SANS_COMPTES=1 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8792 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8793 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8794 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8795 RBI_COURRIEL=1 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8796 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8797 RBI_COURRIEL=1 RBI_COURRIEL_ECHEC=1 \
  node loge/serveur/faux-serveur.mjs &
RBI_PORT=8798 RBI_COURRIEL=1 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8799 RBI_COURRIEL=1 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8800 node loge/serveur/faux-serveur.mjs &
RBI_PORT=8801 node loge/serveur/faux-serveur.mjs &

RBI_URL=http://127.0.0.1:8787/ python3 loge/serveur/essai-documents.py
RBI_URL=http://127.0.0.1:8789/ python3 loge/serveur/essai-partage.py
RBI_URL_SANS=http://127.0.0.1:8788/ RBI_URL_AVEC=http://127.0.0.1:8789/ \
  python3 loge/serveur/essai-verrou.py
RBI_URL_AVEC=http://127.0.0.1:8790/ RBI_URL_SANS=http://127.0.0.1:8791/ \
  python3 loge/serveur/essai-mdp.py
RBI_URL=http://127.0.0.1:8792/ python3 loge/serveur/essai-annuaire.py
RBI_URL=http://127.0.0.1:8793/ python3 loge/serveur/essai-carnet.py
RBI_URL=http://127.0.0.1:8794/ python3 loge/serveur/essai-envois.py
python3 loge/serveur/essai-poste.py
RBI_URL=http://127.0.0.1:8798/ python3 loge/serveur/essai-reponses.py
RBI_URL=http://127.0.0.1:8799/ python3 loge/serveur/essai-pdf.py
RBI_URL=http://127.0.0.1:8800/ python3 loge/serveur/essai-tuilage.py
RBI_URL=http://127.0.0.1:8801/ python3 loge/serveur/essai-odj.py
```

Chaque épreuve veut un serveur NEUF : `essai-mdp` change un mot de
passe, `essai-annuaire` consomme les fiches en attente. Les rejouer
deux fois sur la même instance les fait échouer à bon droit.

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
- **`essai-outil-mdp.mjs`** — le SQL imprimé par `nouveau-mdp.mjs` est
  exécuté sur une vraie base, et l'on entre avec : ce qui est vérifié
  n'est pas un format de texte, c'est que la porte s'ouvre.
- **`essai-gps.mjs`** — le champ du point du Temple lit les deux
  nombres, les degrés, et un lien de plan collé tel quel ; il refuse
  tout le reste, et ne « corrige » jamais deux nombres inversés.
- **`essai-annuaire.py`** — du VRAI formulaire de l'Espace Membres,
  tuilage compris, jusqu'au carnet des Visiteurs : la fiche arrive
  seule, sa case « Tuilé par » reste vide, le même Frère n'entre pas
  deux fois, et seuls les champs attendus sont gardés.
- **`essai-carnet.py`** — un CARNET de contacts s'ajoute sans rien
  effacer, une SAUVEGARDE remplace : les confondre coûterait le Tableau
  de la Loge. Les réserves de lecture suivent la fiche, une adresse
  illisible n'est pas inscrite comme une adresse, le même carnet versé
  deux fois n'ajoute personne, et ce qu'une main a corrigé l'emporte.
- **`essai-envois.py`** — la convocation part-elle à TOUS ? Les Amis
  entrent dans « tout le monde », l'écran annonce la composition, et
  surtout : le lien `mailto:` est MESURÉ. Au-delà du seuil prudent on
  prévient et l'on met les adresses au presse-papier, au lieu de
  laisser la messagerie couper la liste en silence.
- **`essai-poste.py`** — le service d'envoi. AUCUN courriel ne part
  pendant l'épreuve : les appels vers Brevo et Resend sont interceptés
  et l'on vérifie ce qui LEUR aurait été remis. Sans clé configurée le
  bouton n'existe pas ; avec, un seul appel porte tous les messages, un
  par personne ; une adresse glissée dans la requête n'est JAMAIS
  servie ; et quand le service refuse, rien n'est annoncé comme parti.
- **`essai-documents.py`** — la qualité et le contreseing du Souverain
  Grand Commandeur sur chaque document, la feuille des Visiteurs sur sa
  page, le point du Temple sur la convocation.

## Ce qui ne doit jamais entrer ici

Le dépôt est **public**, et Cloudflare Pages sert tout ce qu'il porte.
Aucun nom de Sœur ou de Frère, aucune adresse, aucun mot de passe,
aucune empreinte d'un compte réel — pas même dans un commentaire, pas
même « le temps d'une épreuve ».


## Quand quelqu'un perd son mot de passe

Il n'y a **pas** de « mot de passe oublié », et ce n'est pas un oubli.
Le renvoyer supposerait de pouvoir le relire ; la base n'en garde
qu'une empreinte salée que personne ne sait renverser.

```sh
node loge/serveur/nouveau-mdp.mjs secretariat@exemple.test "le mot neuf"
```

L'outil imprime la ligne `UPDATE` à coller dans la console D1, et ne
calcule rien d'autre — il n'envoie rien, nulle part. Dites ensuite le
mot de vive voix, jamais par courriel : un courriel ne s'efface pas.
Et demandez à l'intéressé de le changer lui-même, par « Mon mot de
passe », dès sa première entrée.

Le même outil crée un compte : la seconde ligne imprimée est l'`INSERT`.


## Faire poster l'Atelier lui-même

Sans configuration, le programme ouvre la messagerie de qui l'utilise —
et un lien `mailto:` trop long est coupé en silence. Avec un service de
courrier, le serveur remet les messages et sait ce qu'il en est.

Dans Cloudflare Pages → Settings → **Variables and Secrets**, en
production :

| Variable | Valeur |
|---|---|
| `BREVO_CLE` *(ou `RESEND_CLE`)* | la clé d'API du service, **en secret** |
| `COURRIEL_EXPEDITEUR` | l'adresse d'expédition, sur un domaine vérifié |
| `COURRIEL_REPONSE` | où doivent arriver les réponses |
| `COURRIEL_NOM` | facultatif — le nom affiché |

### Expédier n'est pas recevoir

C'est ce qui rend l'opération gratuite, et cela mérite d'être compris.

**L'adresse d'expédition** doit appartenir à un domaine vérifié chez le
service — trois lignes dans les réglages DNS du domaine. Elle n'a
besoin d'AUCUNE boîte aux lettres : on expédie depuis
`contact@brith-israel.org` sans que ce domaine ne reçoive quoi que ce
soit. Pas de messagerie à payer.

**L'adresse de réponse** (`COURRIEL_REPONSE`) peut être n'importe
quelle boîte existante — celle qu'on relève déjà. Sans elle, une
réponse partirait vers une adresse que personne ne relève et se
perdrait, sans que ni l'expéditeur ni le destinataire ne s'en doutent.

Expédier depuis une adresse `@gmail.com` par un service tiers passe mal
les filtres : c'est le domaine de l'Atelier qu'il faut vérifier, avec
SPF et DKIM. Une convocation tombée en indésirables est un Frère
absent.

Sans ces variables, rien ne casse : le bouton d'envoi réel n'apparaît
simplement pas, et l'ancien chemin reste.
