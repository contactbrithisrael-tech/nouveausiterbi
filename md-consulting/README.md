# MD Consulting — outil de permanence conseil

Application **locale** (Streamlit + SQLite). Aucune donnée ne quitte la machine :
pas de cloud, pas d'API, pas d'export automatique.

## Installation

```bash
cd md-consulting
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Une seule dépendance : Streamlit. L'export `.docx` est écrit avec la
bibliothèque standard (`docx_minimal.py`), sans `python-docx`.

## Tests

```bash
./lancer_tests.sh
```

106 tests. Les tests d'interface exécutent réellement le script Streamlit
(`st.testing.AppTest`), sans navigateur : ils vérifient entre autres que le
blocage RGPD apparaît bien à l'écran, et pas seulement dans le modèle.

## État d'avancement

| Module | Objet | État |
|---|---|---|
| 1 | Modèle de données + CRUD Personne (RGPD) | fait |
| 2 | Séance + chronomètre | fait |
| 3 | Module Investigation | fait — 12 outils, 447 items |
| 4 | Rapport 4 blocs + export `.docx` | fait |
| 5 | Ressources externes par public | fait |

## Règles RGPD implémentées

- Identifiant technique **UUID**, clé partout. Le nom et le prénom sont des
  données de la fiche, jamais des identifiants.
- **Blocage d'enregistrement** d'un mineur sans date de consentement parental,
  à la création comme à la modification. Le seuil est **18 ans** : tout mineur,
  et un test verrouille cette valeur. Quand la date de naissance est
  renseignée, l'âge exact prime sur la tranche déclarée : une tranche mal
  saisie ne fait pas passer un mineur pour un adulte.
- **Droit à l'effacement** : suppression en une confirmation, avec destruction
  en cascade des séances, résultats et rapports (`ON DELETE CASCADE`).
- Un test passé à l'extérieur n'est stocké que sous forme de **synthèse
  rédigée** : l'outil ne recopie pas les résultats bruts d'un prestataire tiers.
- `.db`, `exports/` et `.docx` sont exclus de Git. Le dépôt étant publié,
  `/md-consulting/*` est en outre renvoyé vers la page d'erreur par
  `_redirects` : Cloudflare ne sert pas le code source.

## Fiche de renseignement (module 1)

Six publics : collège, lycée, reconversion, VAE, handicap, épuisement
professionnel. Ni les publics ni les types de test ne sont figés dans la base :
les contraintes correspondantes sont migrées au démarrage.

Fiche complète, pas de pseudonyme : nom, prénom, date de naissance, téléphone,
courriel, adresse, situation (classe et établissement, ou situation
professionnelle), RQTH, représentant légal et son contact, consentement
parental, lien mescompetences.info, notes libres.

La date de naissance donne l'**âge exact**, en déduit la tranche et décide
seule du consentement parental. Seuil : **18 ans**, verrouillé par un test.

Une fiche incomplète s'enregistre quand même : l'outil liste ce qui manque
plutôt que de bloquer. Seul le consentement parental bloque.

Une base créée avec l'ancienne fiche (pseudonyme) est **migrée
automatiquement** au démarrage : l'ancien nom complet devient le nom, le
prénom reste vide et est signalé comme manquant — il n'est pas deviné en
coupant une chaîne en deux.

## Chronomètre (module 2)

L'instant de départ est relu **en base**, pas en mémoire de session : recharger
la page ne remet pas le compteur à zéro. Trois états — en cours, vigilance
(10 minutes avant le plafond), dépassement. Plafond réglable, 90 minutes par
défaut.

## Compte rendu (module 4) — trame de bilan, assemblée automatiquement

Sept blocs, reprenant la trame d'une synthèse de bilan de compétences **sans
en emprunter l'identité réglementaire** : ni visa des articles R6313-4 et
suivants, ni numéro de certification. Un test l'interdit.

| Bloc | Assemblé depuis | Rendu |
|---|---|---|
| Situation et demande | fiche + date, durée, objectif de la séance | texte |
| Déroulé et outils utilisés | les résultats enregistrés, avec leurs dates | texte |
| Ce qui ressort | les synthèses produites par les grilles des outils | texte |
| Pistes envisagées | **trame vide** : explorées / écartées et pourquoi / retenue | texte |
| Points d'appui et éléments à développer | les cases réellement cochées | **tableau** |
| Plan d'action | les étapes prévues par les outils + lignes libres | **tableau** |
| Références pour affiner | la source de chaque outil + les ressources du public | texte |

L'intitulé du bloc « pistes » et celui du plan d'action suivent le public :
« Pistes d'orientation envisagées » pour un lycéen, « Plan d'action, à rythme
tenable » pour une personne en épuisement.

### Les deux tableaux

Une ligne de texte par ligne de tableau, colonnes séparées par `|`. Le
consultant édite du texte, l'export produit un vrai tableau Word.

- **Points d'appui** : `Savoir-être | Je suis autonome | acquis`. Les
  savoir-être remontent des cases cochées — ce qui a été retenu dans « Points
  forts » est *acquis*, dans « Points de vigilance » *à développer*. Les
  lignes Savoirs et Savoir-faire restent vides : elles dépendent du métier
  visé.
- **Plan d'action** : `Échéance | Action | Moyens`. Les actions sont celles
  que les outils prévoient eux-mêmes après la passation. **Les échéances
  restent vides** — elles se fixent avec la personne, pas depuis une base.

### Ce que l'outil ne remplit pas, et pourquoi

Le bloc **Pistes** arrive vide. Nommer un métier à partir de cases cochées
serait inventer un conseil : c'est la seule chose que l'outil ne fera pas à
la place du consultant. Il pose les trois questions du bilan — explorées,
écartées et pourquoi, retenue — et laisse répondre.

De même, le plan d'action ne prescrit pas les ressources. « Prendre
connaissance de X » imposé à tout le monde serait une démarche inventée ;
les ressources figurent dans les références, où la personne va les chercher.
Un test vérifie qu'aucune URL de ressource n'atterrit dans le plan d'action.

### Le reste

Le bouton **« Tout réassembler depuis la base »** refait les sept blocs et
écrase les retouches. Chaque bloc reste modifiable : ce sont les mots du
consultant qui sont remis.

- **Un outil marqué « donnée de santé » n'apparaît jamais** : rien n'en est
  enregistré, le CBI ne remonte pas.
- **La mise en garde destinée au consultant n'entre pas dans le document** :
  le texte remis vient de `ORIENTATIONS_BENEFICIAIRE`.
- **L'export reste manuel** — la contrainte du projet dit « aucun export ou
  envoi automatique ». Le contenu s'assemble seul, le fichier sort sur un clic.

Un seul compte rendu par séance, garanti par la base. Les bases existantes
sont migrées au démarrage : contrainte d'unicité posée, blocs manquants
ajoutés, rien n'est perdu.

`config.py` porte l'identité imprimée en tête. Les champs sont **vides** :
le document de référence portait les mentions de LinkOm Consultants
(Qualiopi, SIRET, DIRECCTE), qui n'ont pas été recopiées.

## Burn-out : le CBI, jamais enregistré

Le **Copenhagen Burnout Inventory** (domaine public, 19 items, trois
sous-échelles) est intégré à la demande expresse de Mickael Darmon, maintenue
après lecture des réserves. Il en assume l'usage.

Trois garde-fous, tenus par le code et non par la bonne volonté :

- **Rien n'est enregistré.** L'outil porte `donnee_de_sante: true` et n'a pas
  de bouton d'enregistrement : ni les réponses, ni les moyennes, ni le fait de
  l'avoir passé n'atteignent la base. Un score d'épuisement est une donnée de
  santé (article 9). Ce qui doit figurer au compte rendu se rédige à la main.
- **Aucun seuil.** Les auteurs n'en ont pas établi : le fichier ne contient ni
  tranche d'interprétation ni score global. Trois moyennes sur 100, rien
  d'autre. Une moyenne élevée n'est pas un diagnostic.
- **La mise en garde reste affichée** dès que la fiche porte ce public : voie
  de soin, absence de seuil, non-enregistrement.

Le MBI reste exclu — licence payante — et un test le vérifie.

⚠ **La traduction française n'est pas validée** : les propriétés
psychométriques ne sont pas garanties sur cette traduction. Voir
`docs/burn-out.md` pour ce qui n'a pas pu être vérifié.

## Ce qui manque encore — décisions ou fichiers attendus

1. **Mentions légales.** `config.py` attend le nom du consultant et, le cas
   échéant, les coordonnées à imprimer. Rien n'a été inventé.
2. **Déménagement du dépôt — en attente d'une action manuelle.** Ce projet
   vit encore dans le dépôt du site Rite Brith Israël, qui est publié.
   Le paquet Git est prêt et vérifié : voir `docs/depot-separe.md`. La
   création du dépôt ne peut pas être automatisée depuis ici.
3. **Public collège.** Une seule ressource externe le concerne.

## Fichiers

| Fichier | Rôle |
|---|---|
| `schema.sql` | modèle de données complet |
| `db.py` | connexion SQLite, clés étrangères, initialisation |
| `personne.py` | modèle, validation RGPD, CRUD |
| `seance.py` | modèle, chronomètre, CRUD |
| `resultat_test.py` | résultats de tests rattachés à une séance |
| `questionnaire.py` | moteur de questionnaires (7 formes) et calculs |
| `questionnaires/*.json` | les onze outils d'investigation |
| `rapport.py` | compte rendu en quatre blocs |
| `docx_minimal.py` | écriture `.docx` sans dépendance |
| `export_docx.py` | mise en page du compte rendu |
| `ressources.py` | catalogue des ressources externes |
| `dates_fr.py` | affichage des dates au format français |
| `docs/burn-out.md` | le CBI, ses garde-fous et ses limites |
| `config.py` | identité imprimée en tête des rapports |
| `vue_questionnaire.py` | passation, une fonction par forme |
| `vue_*.py` | écrans Streamlit |
| `app.py` | point d'entrée |
