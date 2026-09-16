# Format des questionnaires

Le moteur (`questionnaire.py`) ne contient aucun contenu. Chaque questionnaire
est un fichier JSON déposé dans `questionnaires/`, chargé au démarrage.

```json
{
  "cle": "motivations_35",
  "titre": "Motivations",
  "consigne": "Notez chaque proposition de 1 à 5.",
  "source": "Document original MD Consulting",
  "echelle": { "min": 1, "max": 5, "libelles": { "1": "pas du tout", "5": "tout à fait" } },
  "items": [
    { "id": "m01", "texte": "…", "categorie": "Profil 1" },
    { "id": "m02", "texte": "…", "categorie": "Profil 3" }
  ]
}
```

| Champ | Obligatoire | Rôle |
|---|---|---|
| `cle` | oui | doit correspondre à un `type_test` de `resultat_test.py` |
| `titre` | oui | intitulé affiché |
| `items` | oui | liste non vide ; chaque item porte `id` et `texte`, `id` unique |
| `categorie` | non | regroupe les items ; sert au calcul des totaux |
| `echelle` | non | `min` < `max` ; sans échelle, l'item est une question ouverte |
| `consigne`, `source` | non | affichés tels quels |

Le seul calcul effectué est la **somme des réponses par catégorie**
(`totaux_par_categorie`). C'est ce qui permet une grille de profils : un profil
= une catégorie. Si le document original prévoit une autre règle (pondération,
inversion d'items, seuils), elle devra être décrite avant d'être codée —
elle ne sera pas devinée.

## État

Aucun fichier n'est livré. Les 35 motivations, la grille de profils, les
valeurs, le Projet de vie, les Freins et le Bilan 360° viennent du document
original MD Consulting, transcrit dans `investigation_data.js` — fichier
annoncé dans le brief mais **jamais fourni**. Rien n'a été reconstitué de
mémoire ni inventé.

Dès que le fichier sera disponible, sa conversion vers ce format est une étape
mécanique : une catégorie par profil, un item par proposition.
