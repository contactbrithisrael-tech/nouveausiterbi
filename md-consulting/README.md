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

62 tests. Les tests d'interface exécutent réellement le script Streamlit
(`st.testing.AppTest`), sans navigateur : ils vérifient entre autres que le
blocage RGPD apparaît bien à l'écran, et pas seulement dans le modèle.

## État d'avancement

| Module | Objet | État |
|---|---|---|
| 1 | Modèle de données + CRUD Personne (RGPD) | fait |
| 2 | Séance + chronomètre | fait |
| 3 | Module Investigation | moteur fait, **contenu manquant** |
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

## Ce qui manque encore — décisions ou fichiers attendus

1. **Contenu du module Investigation.** `investigation_data.js` et
   `investigation_prototype.html` n'ont jamais été fournis. Les 35 motivations,
   la grille de profils, les valeurs, le Projet de vie, les Freins et le Bilan
   360° **n'ont pas été reconstitués**. Le moteur les affichera dès qu'ils
   seront déposés au format décrit dans `docs/questionnaires.md`.
2. **Mentions légales.** `config.py` attend le nom du consultant et, le cas
   échéant, les coordonnées à imprimer. Rien n'a été inventé.
3. **Déménagement du dépôt — en attente d'une action manuelle.** Ce projet
   vit encore dans le dépôt du site Rite Brith Israël, qui est publié.
   Le paquet Git est prêt et vérifié : voir `docs/depot-separe.md`. La
   création du dépôt ne peut pas être automatisée depuis ici.
4. **Public collège.** Une seule ressource externe le concerne.

## Fichiers

| Fichier | Rôle |
|---|---|
| `schema.sql` | modèle de données complet |
| `db.py` | connexion SQLite, clés étrangères, initialisation |
| `personne.py` | modèle, validation RGPD, CRUD |
| `seance.py` | modèle, chronomètre, CRUD |
| `resultat_test.py` | résultats de tests rattachés à une séance |
| `questionnaire.py` | moteur générique de questionnaires (contenu externe) |
| `rapport.py` | compte rendu en quatre blocs |
| `docx_minimal.py` | écriture `.docx` sans dépendance |
| `export_docx.py` | mise en page du compte rendu |
| `ressources.py` | catalogue des ressources externes |
| `dates_fr.py` | affichage des dates au format français |
| `config.py` | identité imprimée en tête des rapports |
| `vue_*.py` | écrans Streamlit |
| `app.py` | point d'entrée |
