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

`corpus.json` cartographie **les 33 degrés**. La Roue des Degrés du site
en donne la liste ; là où elle diverge d'un rituel, c'est le rituel qui
fait autorité — deux arbitrages l'ont déjà établi, voir `conflits.md`.

Pour chaque degré : son nom hébreu, sa traduction, sa Séphira, son corps
de rattachement, son équivalent au REAA et ses décors.

Les ateliers se répartissent en **trois catégories**, une par Monde
opératif — article 6 de la Constitution —, plus le Suprême Conseil des
articles 7 et 8 :

| Corps | Monde | Degrés |
|---|---|---|
| Loges Symboliques | Olam Assiah — l'Action | 1 – 3 |
| Loges de Perfection | Olam Yetzirah — la Formation | 4 – 10 |
| Chapitres et Aréopages | Olam Beriah — la Création | 11 – 32 |
| Suprême Conseil | — | 33 |

Il n'y a **pas de Consistoire** : le mot appartient au Rite Écossais, et
la Constitution du Brith Israël ne le connaît pas.

## Ce qui manque

**Quinze ouvrages sont déclarés, et trente-deux degrés sur trente-trois
sont pourvus d'au moins un texte.** Le 33ᵉ n'est couvert par aucun.

Mais tous les textes ne se valent pas, et le compte brut trompe. Ce qui
compte, c'est si un degré dispose d'un ouvrage QUI LUI EST CONSACRÉ, ou
seulement d'un ouvrage qui l'englobe avec vingt et un autres :

| Degrés | Ce qui les couvre | État |
|---|---|---|
| 1 – 3 | un rituel **par degré** (Oved, Boneh, Adon), plus le Tome I et la Bible du Rite | solide |
| 4 – 10 | le **Tome II**, rituels intégraux des Loges de Perfection | solide |
| 11 – 18 | le **Tome III**, rituels intégraux, et la **Bible du Rite Tome III** | solide |
| 19 – 25 | le **Tome IV** | solide, à confirmer |
| 26 – 32 | le Recueil intégral et *Les Trente-Deux Voies* — deux ouvrages qui couvrent vingt-deux degrés chacun | mince |
| 33 | rien | vide |

Le **Tome V** reste à écrire : c'est lui qui pourvoira les 26ᵉ à 32ᵉ.

Le *Plan Maître Tome III* est un **plan de rédaction**, non un ouvrage
d'instruction : il dit ce qui sera écrit, non ce qui s'enseigne. Il ne
doit pas être compté comme une source de degré, et c'est l'avoir compté
qui avait fait croire les 26ᵉ à 32ᵉ pourvus.

### Le Tome IV : porté sur la carte, mais non vérifié

Le **Tome IV** couvre les 19ᵉ à 25ᵉ. Il a été versé dans Joshua Studio et
il est indexé, mais il n'est **pas dans `corpus_rbi/`** : sa plage vient
de la parole du Souverain Grand Commandeur, non de la lecture du fichier.

Elle est donc **à confirmer sur le texte lui-même**, comme l'a exigé le
Tome III — annoncé 11-32 sur la carte, couvrant en fait 11-18. Verser le
fichier au dépôt suffira à trancher.

Il serait présent **en double** dans la bibliothèque du studio. Un
doublon d'empreinte identique est écarté à l'import et inscrit au
registre des doublons ; mais deux *exports différents* du même ouvrage
ont deux empreintes, passent tous les deux, et pèsent alors double dans
les tirages du questionnaire. Cela se règle d'un bouton sur la page
Bibliothèque.

Trois choses manquent encore, et aucune ne s'invente :

1. **Les pages.** Aucun rattachement ne porte de plage de pages. Sans
   elles, Joshua peut lire un ouvrage mais ne peut citer aucune
   référence — or citer est sa règle première.
2. **Les rituels des 26ᵉ à 32ᵉ, et du 33ᵉ.** Le Tome IV s'arrête au 25ᵉ
   et le Tome V reste à écrire. Au-delà du 25ᵉ, aucun texte propre à un
   degré : un questionnaire tiré de là interroge sur de la kabbale
   générale, non sur l'instruction d'un grade.
3. **Rien, côté doctrine.** `conflits.md` est clos : les huit points ont
   été tranchés par les rituels, la Constitution et le Souverain Grand
   Commandeur, et la Roue comme la carte ont été mises d'accord avec eux.
   Ne reste qu'une décision d'administration — la plage d'accès des trois
   ouvrages transversaux.

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
