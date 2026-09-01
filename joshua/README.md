# Joshua — préparation du corpus

Ce dossier ne contient pas Joshua. Joshua tourne ailleurs, sur son propre
serveur. Ce dossier contient ce que Joshua doit recevoir : **la carte du
corpus du Rite et les règles qui la gouvernent**, sous une forme qu'un
programme peut lire.

Il tient lieu de source de vérité. Quand un degré change de rattachement
ou qu'un ouvrage s'ajoute, c'est ici qu'on l'écrit, et Joshua se recharge
depuis ici — jamais l'inverse.

---

## Où sont les textes

Dossier CORPUS RBI sur le Drive du Rite :
<https://drive.google.com/drive/folders/1HKyI7v6s7uFR7Tng80easrtZvv6B7vpl>

Index détaillé, tenu à jour par le Souverain Grand Commandeur :
<https://docs.google.com/document/d/1XHpmPaUdVky7h56pSCPzkz3dBPNolAgPFwjsbgsSofc/edit>

## Où tourne Joshua

Joshua est un bot Telegram, `@RiteBrithIsraelBot`, servi par un Worker
Cloudflare. Il fonctionne à trois modes : Public, Frère/Sœur et Souverain
Grand Commandeur, chacun avec son propre modèle et son propre périmètre.
La carte ci-dessous vaut pour les trois — c'est elle qui décide de ce que
chaque mode peut atteindre.

## Ce qui est établi

`corpus.json` cartographie **les 33 degrés**, extraits de la Roue des
Degrés du site, qui fait autorité. Pour chacun : son nom hébreu, sa
traduction, sa Séphira, son corps de rattachement, son équivalent au REAA
et ses décors.

Les degrés se répartissent en cinq corps :

| Corps | Degrés |
|---|---|
| Loges Symboliques | 1 – 3 |
| Loges de Perfection | 4 – 10 |
| Chapitre — 22 Sentiers | 11 – 30 |
| Consistoire | 31 – 32 |
| Suprême Conseil | 33 |

## Ce qui manque

**Douze ouvrages sont déclarés, et trente-deux degrés sur trente-trois
sont pourvus d'au moins un texte.** Le 33ᵉ n'est couvert par aucun.

Deux choses manquent encore, et aucune ne s'invente :

1. **Les pages.** Aucun rattachement ne porte de plage de pages. Sans
   elles, Joshua peut lire un ouvrage mais ne peut citer aucune
   référence — or citer est sa règle première.
2. **Les arbitrages doctrinaux.** Voir `conflits.md` : la Roue du site et
   les instructions de Joshua se contredisent sur les Séphiroth des
   degrés 7 à 10, sur le nom du 8ᵉ, et sur l'existence d'un Consistoire.
   Indexer avant d'avoir tranché reviendrait à graver une erreur.

---

## Ajouter un ouvrage

Pour chaque volume, trois choses sont nécessaires — et aucune n'est
facultative :

1. **Le texte**, dans un format lisible : PDF avec texte sélectionnable,
   ou fichier de traitement de texte. Un PDF composé d'images scannées ne
   suffit pas : Joshua ne pourrait pas citer de page.
2. **Les degrés qu'il couvre**, et pour chacun les pages exactes. C'est
   cette information qui décide qui verra quoi.
3. **Son statut de diffusion** : réservé aux membres, ou public.

Puis dans `corpus.json` :

```json
"ouvrages": [
  {
    "id": "identifiant-court-sans-espace",
    "titre": "Titre complet de l'ouvrage",
    "nature": "rituel | instruction | commentaire",
    "auteur": "…",
    "degres_couverts": [4, 5, 6],
    "statut": "a_indexer",
    "diffusion": "membres uniquement"
  }
]
```

et, sur chaque degré concerné :

```json
{ "degre": 4,
  "sources": [{ "ouvrage": "identifiant-court-sans-espace",
                "pages": "17-42" }],
  "etat": "declare" }
```

`etat` suit trois valeurs : `a_fournir` tant que le texte manque,
`declare` quand il est rattaché mais pas encore indexé, `indexe` quand
Joshua l'a effectivement chargé.

---

## Les règles, et pourquoi elles ne se négocient pas

### Un membre du degré N voit les degrés 1 à N. Rien au-delà.

Le degré de chacun est fixé par le Souverain Grand Commandeur.

### Le silence sur ce qui est au-dessus

C'est la règle la plus facile à trahir sans le vouloir. Répondre *« ce
document existe, mais votre degré ne vous y donne pas accès »* est **déjà
une divulgation** : cela apprend au Frère qu'il y a quelque chose à
savoir, et à quel degré le chercher. Un système initiatique ne protège pas
seulement le contenu d'un grade, il en protège l'existence.

Joshua répond donc comme si le texte n'existait pas. Ni son titre, ni son
nombre de pages, ni le fait qu'une réponse ait été filtrée ne doivent
transparaître — pas davantage dans un message d'erreur, un compte de
résultats ou un temps de réponse anormalement long.

### Chaque affirmation cite son ouvrage et sa page

Sans référence, pas d'affirmation. C'est ce qui distingue Joshua d'une
intelligence artificielle générale : il ne répond jamais de mémoire.

### Ce qui n'est pas dans les textes, Joshua ne le sait pas

Il ne comble pas les silences du corpus. Il ne tranche aucune question
doctrinale, ne commente pas, et ne remplace ni l'instruction en Loge ni le
Vénérable Maître.

---

## Vérifier la carte

```
python3 joshua/verifier.py
```

Contrôle que les 33 degrés sont présents et sans doublon, qu'aucun n'est
rattaché à deux corps ni à aucun, que chaque source renvoie à un ouvrage
déclaré, que les degrés annoncés par un ouvrage correspondent bien à ceux
qui le citent, et que rien n'est marqué `indexe` sans pages.

Le vérificateur a été éprouvé sur sept cartes volontairement fausses —
degré manquant, degré en double, source orpheline, ouvrage et degrés qui
se contredisent, texte indexé sans pages, état inventé, degré rattaché à
deux corps. Les sept sont détectées.
