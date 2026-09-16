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

46 tests. Les tests d'interface exécutent réellement le script Streamlit
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

- Identifiant technique **UUID** ; le nom complet est un champ séparé,
  facultatif, jamais utilisé comme clé — pas même dans le nom du fichier
  exporté, qui porte le pseudonyme.
- **Blocage d'enregistrement** d'un mineur sans date de consentement parental,
  à la création comme à la modification.
- **Droit à l'effacement** : suppression en une confirmation, avec destruction
  en cascade des séances, résultats et rapports (`ON DELETE CASCADE`).
- Un test passé à l'extérieur n'est stocké que sous forme de **synthèse
  rédigée** : l'outil ne recopie pas les résultats bruts d'un prestataire tiers.
- `.db`, `exports/` et `.docx` sont exclus de Git. Le dépôt étant publié,
  `/md-consulting/*` est en outre renvoyé vers la page d'erreur par
  `_redirects` : Cloudflare ne sert pas le code source.

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
3. **Dépôt séparé.** Ce projet vit dans le dépôt du site Rite Brith Israël,
   qui est publié sur Internet. La règle `_redirects` limite les dégâts ;
   elle ne remplace pas un dépôt dédié.
4. **Seuil du consentement parental.** Réglé sur *tout mineur* (collège et
   lycée). Le brief écrivait « moins de 15 ans », seuil que la tranche collège
   (11-15) chevauche. Une ligne à changer dans `personne.py`.
5. **Public collège.** Une seule ressource externe le concerne.

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
