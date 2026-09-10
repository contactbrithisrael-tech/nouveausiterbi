# Textes à coller dans KDP

Ce dossier n'est pas publié : `_headers` y pose un `X-Robots-Tag: noindex`.
Il tient les textes de vente, versionnés, pour qu'une modification se
retrouve — un texte collé dans KDP puis perdu se réécrit de mémoire, et
de mémoire on n'écrit jamais deux fois la même chose.

## Où coller

KDP → Bibliothèque → sous l'ouvrage, **Modifier les détails du livre** →
champ **Description**. Coller le contenu du fichier tel quel, balises
comprises : le champ interprète le HTML.

La modification doit être faite **sur chaque format séparément** : le
broché et l'ebook Kindle sont deux fiches distinctes, avec chacune sa
description. Compter jusqu'à 72 heures avant que la page Amazon change.

| Fichier | Ouvrage | Broché | Kindle |
|---|---|---|---|
| `description-guide-de-survie.html`     | Guide de Survie pour Franc-Maçon Désemparé | B0GR1WPKR8 | B0GR29BGHN |
| `description-du-petrin-au-compas.html` | Du Pétrin au Compas                        | B0H87J53RG | B0H872YJSX |

## Balises acceptées par KDP

`<br>` `<p>` `<b>` `<em>` `<i>` `<u>` `<h4>` `<h5>` `<h6>` `<ol>` `<ul>` `<li>`

Tout le reste est ignoré ou rejeté : pas de `<div>`, pas de `<span>`,
pas de `<h1>` à `<h3>`, pas de `<img>`, aucun style CSS. Les deux textes
ci-dessus s'y tiennent — vérifié.

Limite : **4000 caractères**, balises comprises.

## Ce qui a changé par rapport aux textes d'origine

**Aucun fait n'a été ajouté.** Les deux textes ne contiennent que ce qui
figurait dans les descriptions fournies par l'auteur. Trois interventions,
et elles seules :

1. **La liste à puces du Guide a été réparée.** L'original portait un
   astérisque orphelin (`: * La résilience`) et enchaînait les trois
   points suivants sans séparateur — un pavé illisible une fois affiché.
2. **La citation d'ouverture du Guide est passée en tête.** Amazon
   tronque la description après deux lignes environ ; ce qui est sous la
   coupure n'est lu que par ceux qui cliquent, c'est-à-dire presque
   personne.
3. **« Une boussole pour tous les chercheurs sans permission »** n'est
   plus entre guillemets, mais en italique. Entre guillemets et sans
   source, la phrase se lit comme une citation de presse ; les règles
   Amazon interdisent les témoignages non sourcés dans ce champ. En
   italique, c'est une accroche d'auteur, ce qu'elle est réellement.

Le mot « indispensable » (« un manuel de résilience éthique
indispensable ») a été retiré : un livre qui se décerne lui-même ce
qualificatif l'affaiblit. C'est le seul retrait, et il se remet en un
mot si l'auteur le veut.
