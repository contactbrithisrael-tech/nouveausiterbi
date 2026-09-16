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

## Tests

```bash
python3 tests/test_personne.py
```
Aucune dépendance externe requise pour les tests (sqlite3 de la bibliothèque standard).

## État d'avancement

| Module | Objet | État |
|---|---|---|
| 1 | Modèle de données + CRUD Personne (RGPD) | fait |
| 2 | Séance + chronomètre 90 min | à venir |
| 3 | Intégration module Investigation | à venir |
| 4 | Rapport 4 blocs + export .docx | à venir |
| 5 | Page de liens externes par public | à venir |

## Règles RGPD implémentées (Module 1)

- Identifiant technique **UUID** ; le nom complet est un champ séparé, facultatif,
  jamais utilisé comme clé.
- **Blocage d'enregistrement** d'un mineur sans date de consentement parental —
  à la création *et* à la modification (impossible de retirer un consentement).
- **Droit à l'effacement** : suppression d'une fiche en une confirmation,
  avec destruction en cascade des séances, résultats de tests et rapports liés
  (`ON DELETE CASCADE`, `PRAGMA foreign_keys = ON`).
- Le fichier `.db`, les exports `.docx` et le dossier `exports/` sont exclus de Git
  par `.gitignore`.

## Point en attente de décision

`CONSENTEMENT_PARENTAL_REQUIS` (dans `personne.py`) est réglé sur **tout mineur**
(collège *et* lycée). Le brief mentionnait « moins de 15 ans », seuil que la tranche
« collège » (11-15 ans) chevauche. Modifier une seule ligne pour revenir à la lettre
du brief.

## Fichiers

- `schema.sql` — modèle de données complet (personne, seance, resultat_test, rapport)
- `db.py` — connexion SQLite, activation des clés étrangères, initialisation
- `personne.py` — modèle, règles de validation RGPD, CRUD
- `vue_personne.py` — formulaire de fiche et bloc de suppression
- `app.py` — point d'entrée Streamlit
