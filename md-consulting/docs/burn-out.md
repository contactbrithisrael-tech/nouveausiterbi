# Burn-out : le CBI, et à quelles conditions

## La décision

Le Copenhagen Burnout Inventory est intégré à l'outil **à la demande expresse
de Mickael Darmon**, maintenue après lecture des réserves ci-dessous. Il en
assume l'usage professionnel. Ce document existe pour que la décision et ses
garde-fous restent lisibles dans six mois.

Les réserves, rappelées telles qu'elles ont été posées :

1. **L'épuisement professionnel relève de la santé au travail** — médecin du
   travail, médecin traitant, psychologue — et non d'une permanence de conseil
   en orientation. Faire passer une échelle et annoncer un résultat à quelqu'un
   qu'on ne peut ni diagnostiquer ni soigner le met en difficulté.
2. **Un score d'épuisement est une donnée de santé**, au sens de l'article 9
   du RGPD.
3. **Le burn-out ne se « détecte » pas par un questionnaire.** L'INRS le
   rappelle : dans les classifications médicales internationales, ce n'est pas
   une maladie mais un phénomène lié au travail. Les échelles existantes
   mesurent, elles ne diagnostiquent pas.
4. **L'instrument de référence est payant.** Le MBI est sous licence exclusive
   facturée à l'administration. Il reste exclu, et un test le vérifie.

## L'instrument retenu

**Copenhagen Burnout Inventory (CBI)** — domaine public, conçu comme
l'alternative libre au MBI.

Publication d'origine : Kristensen, Borritz, Villadsen & Christensen,
« The Copenhagen Burnout Inventory : a new tool for the assessment of
burnout », *Work & Stress*, 2005.

19 items, trois sous-échelles :

| Sous-échelle | Items |
|---|---|
| Épuisement personnel | 6 |
| Épuisement lié au travail | 7 |
| Épuisement lié aux personnes accompagnées | 6 |

Échelle à cinq degrés, cotés **0 · 25 · 50 · 75 · 100**. Chaque sous-échelle
donne une **moyenne sur 100**. Un item est **inversé** — « Avez-vous assez
d'énergie pour votre famille et vos amis pendant votre temps libre ? » : une
énergie conservée compte comme un épuisement absent.

## Les trois garde-fous, tenus par le code

### Rien n'est enregistré

L'outil porte `donnee_de_sante: true`. Il n'a **pas de bouton
d'enregistrement** : ni les réponses, ni les moyennes, ni le fait même de
l'avoir passé n'atteignent la base. L'écran affiche le résultat, puis
« Fermer sans rien conserver » efface tout de la session.

Ce qui doit figurer au compte rendu est à rédiger à la main, sous la
responsabilité du consultant.

Deux tests le vérifient : l'un que le bouton d'enregistrement n'existe pas et
que la base reste vide après ouverture ; l'autre qu'aucun autre outil du
dossier ne porte cette marque par accident.

### Aucun seuil

Les auteurs n'ont pas établi de seuil diagnostique individuel. Le fichier ne
contient donc **aucune tranche d'interprétation** et **aucun score global** :
trois moyennes, rien d'autre. Un test échoue si un seuil est ajouté.

Une moyenne élevée n'est pas un diagnostic de burn-out.

### La mise en garde reste affichée

Dès qu'une fiche porte le public « épuisement professionnel », l'écran de
séance et celui des ressources rappellent la voie de soin, l'absence de seuil
et le non-enregistrement. Un test la lit à l'écran.

## Ce que je n'ai pas pu vérifier

**La traduction française n'est pas validée.** Les items ci-dessous sont une
traduction de travail des items anglais. Les propriétés psychométriques de
l'instrument ne sont **pas garanties** sur cette traduction. Une version
française validée existe peut-être ; je n'ai pas pu la vérifier.

**L'ordre des items à l'intérieur de la sous-échelle « liée au travail »**
provient de deux sources concordantes, non de la publication d'origine lue
directement — les dépôts qui la diffusent sont bloqués par le proxy réseau de
l'environnement de développement. Le rattachement aux trois sous-échelles
(6 / 7 / 6) est en revanche établi, et c'est lui seul qui détermine le calcul.

Avant tout usage réel, récupérer l'instrument depuis la publication d'origine
et comparer.

## Orienter reste la règle

Deux ressources vérifiées, rattachées à ce public :

- **INRS — Épuisement professionnel** : la référence française. Définition,
  facteurs de risque, cadre de prévention.
- **Mon soutien psy (Assurance Maladie)** : séances chez un psychologue
  partiellement remboursées, **sans prescription préalable**, annuaire sur
  ameli.fr. La personne prend rendez-vous elle-même.

Passer le CBI n'exonère pas d'orienter. C'est écrit dans la mise en garde.
