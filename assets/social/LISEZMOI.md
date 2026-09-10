# Visuels de promotion

**Ce dossier est produit par un script. Ne rien y retoucher à la main :
la prochaine exécution écrase tout.**

    node outils/generer-visuels.mjs

Le contenu se modifie dans `outils/visuels/cartes.mjs`, l'apparence dans
`outils/visuels/gabarits.mjs`. Ajouter une citation revient à ajouter
une entrée et relancer.

## Deux formats, deux usages

| Suffixe | Taille | Où |
|---|---|---|
| `-paysage` | 1200 × 630 | Facebook, LinkedIn, aperçus de lien, courriels |
| `-carre`   | 1080 × 1080 | Instagram, partages en messagerie |

## Ce qu'il y a dedans

- `citation-perfection` · `citation-ombres` — Guide de Survie
- `citation-verite` · `citation-loge` — Du Pétrin au Compas
- `auteur-parcours` — le parcours de l'auteur
- `livre-guide` · `livre-petrin` — fiche par ouvrage, avec la couverture

## Comment s'en servir

**Une image par publication.** Deux couvertures dans un même message
divisent l'attention, et Facebook n'en affiche correctement qu'une.

**Les cartes de citation valent mieux que les cartes de livre** pour une
publication ordinaire : une citation se lit et se partage, une couverture
avec un lien se lit comme une publicité et se fait dérouler.

**`auteur-parcours` est la plus distinctive.** Aucun autre livre du rayon
ne peut reprendre cet argument. À réserver aux moments où il faut
convaincre quelqu'un qui ne connaît pas l'auteur — une prise de contact
avec une obédience, un blog maçonnique, une première publication.

Les couvertures sont relues à chaque exécution depuis `assets/images.js`.
Remplacer une couverture là suffit : tous les visuels suivent.
