# Format des questionnaires

Le moteur (`questionnaire.py`) ne contient aucun contenu. Chaque outil est un
fichier JSON dans `questionnaires/`, chargé au démarrage et validé à la lecture.
Ajouter un outil ne demande aucune modification du code ni de la base.

Champs communs : `cle` (identifiant, sert de `type_test`), `titre`, `forme`,
`source` (obligatoire à l'usage : d'où vient ce contenu), et facultativement
`consigne`, `introduction`, `note` (affichée en avertissement), `suite`
(étapes papier à faire après la passation).

## Les sept formes

### `checklist`
Liste à cocher. `items: [{id, texte, definition?}]`. La définition s'affiche
en italique à côté de l'item. Utilisée par *freins*, *valeurs*,
*points_forts*, *points_vigilance*.

### `choix_groupes`
Questions à choix multiples rangées par sections.
`sections: [{titre, questions: [{id, texte, choix: [...], multiple}]}]`.
Utilisée par *projet_de_vie*.

### `selection_n`
Choisir N items dans une liste, puis compter combien tombent dans chaque
profil. `nb_a_selectionner`, `items`, et
`profils: {"Profil 5": {items: [...], description: "..."}}`.
**La validation exige que la grille couvre exactement les items**, une fois
chacun : une grille tronquée est refusée au chargement. Utilisée par
*motivations_35*.

### `likert`
Affirmations notées sur une échelle. `echelle: [{libelle, points}]`,
`interpretation: [{min, max, texte}]` pour le score global, et
`thematiques: [{nom, lecture, axe_de_travail, items: [...]}]`.
Une thématique dont `items` est vide n'est pas calculée — elle n'est pas
devinée. Utilisée par *predisposition_creation_entreprise*.

### `ab`
Choix forcé entre deux propositions. `items: [{id, a, b}]` et
`axes: [{nom, cle: {item: "A"|"B"}, lecture: {haut, bas, seuil}}]`.
**La validation exige que les clés de cotation couvrent exactement les
items** : une clé incomplète est refusée. Utilisée par
*orientation_formateur*.

### `matrice_360`
Items croisés avec des évaluateurs. `evaluateurs`, `niveaux`,
`groupes: [{titre, items}]`. L'écran fait remplir une colonne à la fois et
signale les **écarts de perception** entre évaluateurs. Utilisée par
*bilan_360* et *bilan_360_scolaire*.

### `questions_ouvertes`
Questions à réponse libre, avec un `entete` facultatif (date, interlocuteur…).
Utilisée par *enquete_metier*.

## Outils installés

| Clé | Forme | Items |
|---|---|---|
| `projet_de_vie` | choix_groupes | 25 questions, 10 sections |
| `freins` | checklist | 26 |
| `motivations_35` | selection_n | 35 + grille 5 profils |
| `valeurs` | checklist | 48 avec définitions |
| `points_forts` | checklist | 64 |
| `points_vigilance` | checklist | 33 |
| `bilan_360` | matrice_360 | 68 × 6 évaluateurs |
| `bilan_360_scolaire` | matrice_360 | 68 × 7 évaluateurs |
| `enquete_metier` | questions_ouvertes | 11 |
| `predisposition_creation_entreprise` | likert | 20, score /80 |
| `orientation_formateur` | ab | 30, 2 axes, 5 familles |

Les effectifs sont **vérifiés par un test** (`tests/test_questionnaires.py`) :
une transcription tronquée fait échouer la suite.

## Ciblage par public

Chaque outil déclare les publics auxquels il convient (`publics`) et **justifie
ce choix** (`note_publics`). L'écran de séance ne propose que les outils
rattachés au public de la personne reçue, et dit combien ont été écartés.

| Outil | Collège | Lycée | Reconv. | VAE | Handicap | Burn-out |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| valeurs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| points_forts | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| points_vigilance | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| bilan_360_scolaire | ✓ | ✓ | | | | |
| bilan_360 | | | ✓ | ✓ | ✓ | ✓ |
| projet_de_vie | | ✓ | ✓ | ✓ | ✓ | ✓ |
| freins | | ✓ | ✓ | ✓ | ✓ | ✓ |
| motivations_35 | | ✓ | ✓ | ✓ | ✓ | ✓ |
| enquete_metier | | ✓ | ✓ | ✓ | ✓ | ✓ |
| predisposition_creation_entreprise | | | ✓ | ✓ | | |
| orientation_formateur | | | ✓ | ✓ | | |

**Ces rattachements sont des propositions**, chacune modifiable en une ligne
dans le fichier de l'outil. Les raisons retenues :

- Le questionnaire *Valeurs* tutoie (« Sélectionne ce qui est important pour
  toi dans la vie ») : il est écrit pour être utilisable avec des jeunes.
  C'est le seul du lot dans ce cas.
- *Bilan 360°* existe en deux versions dans le document : celle aux colonnes
  Parents et Extrascolaire va aux scolaires, celle aux colonnes Responsable
  et Collègue aux adultes.
- *Freins*, *Motivations*, *Projet de vie* parlent de vie salariée — permis de
  conduire, chômage de longue durée, CDI, statut de fonctionnaire, salaire.
  Écartés du collège.
- *Prédisposition à la création d'entreprise* est écarté du burn-out :
  mesurer une appétence entrepreneuriale pendant un épuisement professionnel
  demande l'arbitrage du consultant, pas un réglage par défaut.

## Ce qui est écarté pour une personne mineure

Un item peut être retiré d'un questionnaire quand la personne est mineure,
via `items_ecartes_si_mineur`. Un seul l'est aujourd'hui :

> **Valeurs, item v05 — « Amour : affection envers les autres, intimité
> sexuelle ».** Cet énoncé n'a pas à être soumis à un collégien dans un
> entretien de conseil. Il est écarté d'office pour toute personne mineure ;
> l'écran indique au consultant ce qui a été retiré. Retirer `v05` de la liste
> pour revenir au document.

Un item peut aussi porter un champ `sensible`, affiché en avertissement :

> **Valeurs, item v18 — « Religion : spiritualité, vénération et culte ».**
> Une conviction religieuse cochée et enregistrée est une donnée sensible au
> sens de l'article 9 du RGPD. L'item est conservé — c'est une valeur
> légitime en bilan — mais l'écran le signale.

**Aucun énoncé n'a été réécrit.** Adapter la formulation d'un item revient à
le reformuler, ce que la règle du projet interdit et qui, pour un instrument
soumis à des mineurs, ne relève pas d'un choix technique. Les items qui
gênent sont écartés ou signalés, jamais réécrits.

## Provenance

Tout ce contenu est transcrit des documents MD Consulting fournis :
*S2 OUTILS BDC INVESTIGATION — Motivations, valeurs, qualités* (23 pages
scannées), *enquete-metier_MD_CONSULTING.docx*,
*Test_predisposition_Creation_dEntreprise_LINKOM_CONSULTANTS.docx* et
*test_Formateur.docx*. Rien n'a été inventé, reformulé ni complété.

## Quatre points à trancher

1. **Motivations : 10 ou 7 ?** Le document contient deux versions de la même
   liste de 35. La première demande d'en sélectionner **10**, la seconde d'en
   entourer **7**. La grille d'interprétation est identique. C'est la version
   à 10 qui est installée (`nb_a_selectionner`).
2. **Test création d'entreprise : thématiques non rattachées.** La colonne
   « Items liés » de la fiche d'analyse est vide dans le document. Les six
   moyennes thématiques ne sont donc pas calculables. Le score global l'est.
3. **Orientation formateur : seuil à exactement 10.** Le document lit
   « TOTAL > 10 » et « TOTAL < 10 » sans dire de quel côté tombe un score de
   10 pile. L'outil le range du côté bas ; à confirmer.
4. **Orientation formateur : droits d'auteur.** La grille est celle de Noyé et
   Piveteau, un instrument publié. Sa reproduction dans un logiciel est une
   question distincte du RGPD, à vérifier avant tout usage hors pratique
   personnelle du consultant.
