# Gabarit de rapport — structure de référence

Structure relevée sur une synthèse de bilan de compétences réelle fournie
par Mickael Darmon. **Seule l'ossature est reproduite ici : aucun contenu
nominatif, aucune donnée de bénéficiaire.**

## 1. Document de référence

Synthèse de bilan de compétences émise sous en-tête **LinkOm Consultants**
(organisme de formation, certificat Qualiopi, n° SIRET et n° DIRECCTE en
pied de page), visant les **articles R6313-4 à R6313-8 du code du travail**.
Consultant : Mickael Darmon. Volume : 24 heures (16 h de rendez-vous dont
2 h de passation/restitution de tests, 8 h de travail personnel).

### Ossature

**Page de garde** — Bénéficiaire (nom, prénom) · Consultant (nom, prénom) ·
date de début et date de fin du bilan.

**PHASE I — phase préliminaire : « Circonstances du bilan de compétences »**
- A. Le parcours professionnel
- B. Le contexte de la demande et les attentes du bénéficiaire
- C. L'objectif du bilan de compétences
- D. Parcours de bilan — objectifs des trois phases, rythme des rendez-vous,
  rappel des règles de confidentialité et de la charte déontologique

**PHASE II — phase d'investigations : « Investigations et projet professionnel »**
- A. Intitulé du métier ou de la fonction visée
- B. Éléments constitutifs du projet
  - a. Résultats et analyse des tests au regard du projet
  - b. Résultat des investigations et enquêtes métiers
    - i. Liste des métiers investigués
    - ii. Les métiers non retenus, et pourquoi
    - iii. Le ou les métiers retenus
  - c. Analyse des compétences requises — **tableau** à trois colonnes
    (*acquis* / *partiellement acquis* / *à acquérir*) et trois blocs de
    lignes : **SAVOIRS**, **SAVOIR-FAIRE**, **SAVOIR-ÊTRE (soft skills)**
  - d. Les besoins au regard du projet
  - e. Analyse des motivations et des valeurs au regard du projet
  - f. Exercice de technique projective

**PHASE III — phase de conclusions : « Plan d'action / Solutions alternatives »**
- A. Le plan d'action — **tableau** : *Date échéance* | *Action(s) à réaliser* |
  *Moyen(s) nécessaire(s)*
- B. Conclusion
- Signatures : le consultant, le bénéficiaire

## 2. État : la trame est implémentée

Le compte rendu produit par l'outil suit désormais cette ossature, en sept
blocs, sans en emprunter l'identité réglementaire. Voir la section
« Compte rendu » du README pour le détail de ce qui s'assemble seul.

## 3. Correspondance d'origine avec les 4 blocs du brief

| Bloc du brief | Provenance dans la structure de référence |
|---|---|
| `bloc_situation` | Phase I, A + B + C |
| `bloc_tests_utilises` | Phase I, D (outils annoncés) + Phase II, B.a |
| `bloc_resultats` | Phase II, B.a / B.c / B.d / B.e |
| `bloc_solutions` | Phase III, A (tableau d'actions) + B |

La correspondance est bonne. Deux emprunts sont directement réutilisables :
le **tableau de compétences** à trois niveaux d'acquisition et le **tableau
de plan d'action** daté avec les moyens nécessaires — ce dernier remplit
exactement la fonction « pistes concrètes + prochaines démarches » du brief.

## 4. Points tranchés

1. **Sous quelle entité ?** Le document de référence est émis par *LinkOm
   Consultants*, avec numéro Qualiopi, SIRET et DIRECCTE. Le présent outil
   s'appelle *MD Consulting*. Mentions légales à confirmer avant de les
   imprimer sur un document remis à une personne.
2. **Le mini-rapport n'est pas un bilan de compétences.** Le brief le dit :
   séance de 1 h à 1 h 30, « pas un bilan de compétences complet ». Le
   document de référence est, lui, la synthèse réglementaire d'un bilan de
   24 heures. Reprendre sa charte, ses numéros d'agrément et son plan
   produirait un document qui *ressemble* à une synthèse réglementaire sans
   en être une. Le gabarit doit s'en inspirer, mais porter un titre distinct
   et ne pas viser les articles R6313-4 à R6313-8.
3. **Adaptation scolaire.** Les rubriques « métiers non retenus », « enquête
   métier », « compétences acquises » n'ont pas de sens tel quel pour un
   collégien. Le brief prévoit des blocs identiques et un contenu adapté :
   reste à définir les intitulés pour les publics collège et lycée.
