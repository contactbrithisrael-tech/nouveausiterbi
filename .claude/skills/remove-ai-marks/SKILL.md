---
name: remove-ai-marks
description: Retire d'un texte les caractères invisibles, espaces exotiques et homoglyphes qui cassent la recherche, les diff et l'extraction. Utiliser quand un texte contient des caractères parasites, qu'une recherche échoue sans raison apparente, qu'un diff signale une ligne identique comme modifiée, ou avant d'indexer, publier ou comparer du texte venu d'un traitement de texte, d'un PDF ou d'un copier-coller.
---

# Nettoyage des marques invisibles

## Quand l'utiliser

- une recherche échoue sur une chaîne pourtant visible à l'écran
- un `diff` signale une ligne modifiée alors qu'elle paraît identique
- un texte vient d'un PDF, d'un traitement de texte ou d'un copier-coller
- avant d'indexer, de publier ou de comparer du texte

## Ce que l'outil fait

| Famille | Exemples | Traitement |
|---|---|---|
| Invisibles | espace sans chasse, BOM, trait d'union conditionnel | supprimés |
| Directionnels | marques et isolats bidirectionnels | supprimés |
| Espaces exotiques | insécable, fine, cadratin, idéographique | ramenées à l'espace ordinaire |
| Homoglyphes | `О` cyrillique, `Ο` grec dessinés comme `O` | corrigés **en contexte latin uniquement** |
| Formes Unicode | `e` + accent combinant | normalisées en NFC |

## Ce que l'outil ne fait pas

Il **ne réécrit pas le style** et ne déguise rien : il retire des
caractères parasites, il ne touche pas aux mots. Un texte propre en
ressort identique octet pour octet — c'est cette propriété qui permet de
le passer sans crainte sur n'importe quel fichier.

## Utilisation

```bash
S=~/.claude/skills/remove-ai-marks/nettoyer.py

python3 "$S" fichier.md                 # rapport, sans modification
python3 "$S" --ecrire fichier.md         # modifie sur place
python3 "$S" --verifier *.md             # code de sortie 1 si une marque est trouvée
cat texte.txt | python3 "$S" > propre.txt
```

### Options

| Option | Effet |
|---|---|
| `--ecrire` | modifie les fichiers sur place, seulement s'ils changent vraiment |
| `--verifier` | ne modifie rien ; sort en erreur si une marque est trouvée — utilisable en intégration continue |
| `--fr` | rétablit les insécables de la typographie française (`;` `:` `!` `?` `«` `»`) |
| `--sans-liants` | retire aussi ZWJ et ZWNJ |
| `--sans-nfc` | n'applique pas la normalisation NFC |

## Deux règles à ne pas contourner

**Les liants ZWJ et ZWNJ sont conservés par défaut.** Ils sont
invisibles, mais ils portent du sens en arabe, en hébreu et dans les
écritures indiennes. Ne poser `--sans-liants` que sur du texte dont on
sait qu'il n'en contient pas.

**Les homoglyphes ne sont corrigés qu'en contexte latin.** Un mot dont
une seule lettre n'a pas de jumelle latine — le `к` de « Москва », le
`γ` de « Λόγος » — est laissé intact. Une substitution globale
détruirait tout texte réellement russe, grec ou hébreu.

## Vérification

```bash
python3 -m pytest ~/.claude/skills/remove-ai-marks/test_nettoyer.py -q
```

28 tests, dont ceux qui vérifient qu'un texte propre, du russe, du grec
et de l'hébreu ressortent **inchangés**.
