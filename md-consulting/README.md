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

94 tests. Les tests d'interface exécutent réellement le script Streamlit
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

## Compte rendu (module 4)

Quatre blocs pour tous les publics ; seul l'intitulé du dernier change
(« Pistes d'orientation » pour un lycéen, « Démarches VAE » pour une VAE…).

**Un seul bloc est rempli par l'outil** : la liste des outils utilisés, reprise
de la base. Les trois autres sont rédigés par le consultant. Un compte rendu
remis à quelqu'un n'est pas un texte généré.

`config.py` porte l'identité imprimée en tête. Les champs sont **vides** :
le document de référence fourni portait les mentions de LinkOm Consultants
(Qualiopi, SIRET, DIRECCTE), qui n'ont pas été recopiées. Un test vérifie
qu'aucune mention réglementaire n'apparaît dans la configuration.

## Module Investigation (module 3)

Douze outils installés, 447 items :

| Outil | Forme | Items |
|---|---|---|
| Questionnaire Projet de vie | 25 questions en 10 sections | 25 |
| Les freins au travail | liste à cocher | 26 |
| Les motivations au travail | choisir 10 sur 35, grille 5 profils | 35 |
| Mes valeurs | liste à cocher avec définitions | 48 |
| Points forts | liste à cocher | 64 |
| Points de vigilance | liste à cocher | 33 |
| Bilan personnel 360° | 68 items × 6 évaluateurs | 68 |
| Grille 360° version scolaire | 68 items × 7 évaluateurs | 68 |
| Enquête métier | questions ouvertes | 11 |
| Prédisposition à la création d'entreprise | échelle, score /80 | 20 |
| Orientation formateur | choix forcé, 2 axes, 5 familles | 30 |
| Copenhagen Burnout Inventory | 3 sous-échelles, moyennes /100 | 19 |

Le moteur ne contient aucun contenu : chaque outil est un fichier JSON dans
`questionnaires/`. En ajouter un ne demande ni code ni migration de base.
Les effectifs et les grilles sont vérifiés par des tests — la grille des
motivations doit couvrir les 35 items une fois chacun, la clé du test
formateur ses 30 items, sinon le chargement est refusé.

Le module 360° signale les **écarts de perception** entre évaluateurs.

**Chaque outil est rattaché à des publics** et l'écran de séance ne propose
que ceux qui conviennent à la personne reçue : 4 outils pour un collégien,
8 pour un lycéen, 10 pour un adulte en reconversion. Le Bilan 360° existe en
deux versions, scolaire (colonnes Parents, Extrascolaire) et adulte
(Responsable, Collègue).

Un énoncé peut être **écarté pour une personne mineure** — l'item
« Amour : affection envers les autres, intimité sexuelle » du questionnaire
Valeurs l'est d'office, et l'écran dit au consultant ce qui a été retiré.
Aucun énoncé n'est réécrit : ce qui gêne est écarté ou signalé.

Détail du format et points à trancher : `docs/questionnaires.md`.

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
