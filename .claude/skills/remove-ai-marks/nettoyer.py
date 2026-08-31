#!/usr/bin/env python3
"""Nettoyage des marques invisibles laissées dans un texte.

Ce que l'outil traite
---------------------
Trois familles de caractères qui se voient rarement à l'écran et cassent
tout le reste : recherche plein texte, ``diff``, tri, extraction PDF,
comparaison de mots de passe, correspondance d'URL.

1. Les INVISIBLES : espaces de largeur nulle, marque d'ordre des octets,
   trait d'union conditionnel. Ils occupent une position dans la chaîne
   sans occuper de place à l'écran, donc « joshua » et « jo<U+200B>shua »
   paraissent identiques et ne le sont pas.
2. Les ESPACES EXOTIQUES : insécable, fine, cadratin. Elles se voient,
   mais comme des espaces ordinaires. Une recherche de « Rite Brith »
   échoue si le texte contient une insécable entre les deux mots.
3. Les HOMOGLYPHES : lettres cyrilliques ou grecques dessinées comme des
   latines. « Ореn » et « Open » se ressemblent au pixel près.

Ce que l'outil ne fait PAS
--------------------------
Il ne réécrit pas le style et ne « déguise » rien : il retire des
caractères parasites, il ne touche pas aux mots. Un texte propre en
ressort identique — c'est la propriété qui rend l'outil sûr à passer sur
n'importe quel fichier.

Décisions à justifier
---------------------
Les homoglyphes ne sont remplacés que DANS UN MOT PAR AILLEURS LATIN. Une
substitution globale détruirait tout texte réellement russe ou grec, et
ce corpus contient de l'hébreu, du grec translittéré et des citations en
alphabets multiples. Le contexte est donc la seule règle défendable.

Les liants ZWJ et ZWNJ sont conservés par défaut. Ils sont invisibles,
mais ils portent du sens en arabe, en hébreu et dans les écritures
indiennes : les retirer sans le dire corromprait le texte au lieu de le
nettoyer. ``--sans-liants`` les retire pour qui sait ce qu'il fait.

L'espacement français est une OPTION. Convertir toutes les espaces en
espace ordinaire est correct pour du texte technique et faux pour de la
prose française, où l'insécable devant « ; : ! ? » et à l'intérieur des
guillemets fait partie de l'orthographe. ``--fr`` rétablit ces
insécables APRÈS le nettoyage, plutôt que d'essayer de deviner
lesquelles conserver.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

# ── Invisibles ──────────────────────────────────────────────────────
#: Caractères sans largeur. Retirés purement et simplement.
INVISIBLES = {
    "​": "espace sans chasse",
    "⁠": "gluon",
    "﻿": "marque d'ordre des octets",
    "­": "trait d'union conditionnel",
    "͏": "gluon de graphèmes",
    "᠎": "séparateur de voyelle mongol",
    "⁡": "application de fonction",
    "⁢": "multiplication invisible",
    "⁣": "séparateur invisible",
    "⁤": "addition invisible",
}
#: Liants : invisibles mais SIGNIFIANTS dans plusieurs écritures.
LIANTS = {"‌": "antiliant sans chasse", "‍": "liant sans chasse"}
#: Marques de direction. Elles n'ont de sens que dans un texte
#: bidirectionnel mis en forme ; dans un fichier source elles ne font
#: que déplacer le curseur de façon incompréhensible.
DIRECTIONNELS = {
    "‎": "marque gauche-à-droite",
    "‏": "marque droite-à-gauche",
    **{c: "contrôle bidirectionnel" for c in "‪‫‬‭‮"},
    **{c: "isolat bidirectionnel" for c in "⁦⁧⁨⁩"},
}

# ── Espaces ─────────────────────────────────────────────────────────
ESPACES = {
    " ": "espace insécable",
    " ": "espace fine insécable",
    " ": "espace chiffre",
    " ": "espace fine",
    " ": "espace ultrafine",
    " ": "demi-cadratin",
    " ": "cadratin",
    " ": "tiers de cadratin",
    " ": "quart de cadratin",
    " ": "sixième de cadratin",
    " ": "espace de ponctuation",
    " ": "espace mathématique",
    "　": "espace idéographique",
}

# ── Homoglyphes ─────────────────────────────────────────────────────
#: Cyrillique et grec vers latin. Uniquement les paires dont le dessin
#: est identique dans les polices courantes : une ressemblance
#: approximative ne justifie pas de modifier le texte de quelqu'un.
HOMOGLYPHES = {
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X", "Ѕ": "S", "І": "I",
    "Ј": "J", "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y",
    "х": "x", "ѕ": "s", "і": "i", "ј": "j",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
    "ο": "o", "ν": "v", "ρ": "p",
}

_LATIN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
_MOT = re.compile(r"[^\W\d_]+", re.UNICODE)


def _mot_latin(mot: str) -> bool:
    """Vrai si le mot ne peut être qu'un mot latin déguisé.

    C'est le test qui protège les textes réellement écrits en cyrillique,
    en grec ou en hébreu. Deux conditions, et il faut les deux :

    - **toute lettre non latine du mot doit être un homoglyphe connu.**
      Une seule lettre étrangère sans jumelle latine — le « к » de
      « Москва », le « γ » de « Λόγος » — suffit à prouver que le mot
      appartient à cette écriture, et le mot est laissé intact ;
    - **le mot doit contenir au moins une lettre latine authentique.**
      Sans elle, rien ne distingue un mot latin déguisé d'un vrai mot
      court dans une autre écriture.

    Compter les lettres et exiger une majorité latine, comme on serait
    tenté de le faire, échoue sur le cas le plus courant : « Ореn » ne
    garde qu'une seule lettre latine sur quatre.
    """
    latines = 0
    suspectes = 0
    for caractere in mot:
        if caractere in HOMOGLYPHES:
            suspectes += 1
        elif _LATIN.match(caractere):
            latines += 1
        else:
            return False
    return latines > 0 and suspectes > 0


def _corriger_homoglyphes(texte: str) -> tuple[str, int]:
    corriges = 0

    def remplacer(trouve: re.Match) -> str:
        nonlocal corriges
        mot = trouve.group(0)
        if not _mot_latin(mot):
            return mot
        corriges += sum(1 for c in mot if c in HOMOGLYPHES)
        return "".join(HOMOGLYPHES.get(c, c) for c in mot)

    return _MOT.sub(remplacer, texte), corriges


# ── Espacement français ─────────────────────────────────────────────
#: Ponctuations hautes, qui prennent une espace fine insécable AVANT.
_PONCTUATION_HAUTE = ";:!?»"
_AVANT = re.compile(r"[ \t]*([;:!?»])")
_APRES = re.compile(r"(«)[ \t]*")


def _espacement_francais(texte: str) -> str:
    """Rétablit les insécables de la typographie française.

    Appliqué APRÈS le nettoyage, pas à sa place. Deviner lesquelles des
    insécables d'origine étaient légitimes est impossible ; les retirer
    toutes puis reposer celles que la règle impose donne un résultat
    déterministe, quel que soit l'état du texte d'entrée.

    Les deux-points d'une URL ou d'un horaire ne prennent pas d'espace :
    la règle ne s'applique donc que si le signe est déjà précédé d'une
    espace ou d'un mot, jamais accolé à un chiffre ou à un schéma.
    """
    def avant(trouve: re.Match) -> str:
        signe = trouve.group(1)
        debut = trouve.start()
        precedent = texte[debut - 1] if debut else " "
        # « 12:30 », « https:// » : pas d'espace fine.
        if signe == ":" and (precedent.isdigit() or texte[max(0, debut - 5):debut].isalpha()
                             and texte[trouve.end():trouve.end() + 2] == "//"):
            return trouve.group(0)
        return " " + signe

    texte = _AVANT.sub(avant, texte)
    return _APRES.sub("« ", texte)


# ── Nettoyage ───────────────────────────────────────────────────────
def nettoyer(texte: str, sans_liants: bool = False, francais: bool = False,
             normaliser: bool = True) -> tuple[str, dict[str, int]]:
    """Retourne le texte nettoyé et le compte par famille de marque."""
    compte: dict[str, int] = {}

    a_retirer = dict(INVISIBLES)
    a_retirer.update(DIRECTIONNELS)
    if sans_liants:
        a_retirer.update(LIANTS)

    sortie = []
    for caractere in texte:
        if caractere in a_retirer:
            compte[a_retirer[caractere]] = compte.get(a_retirer[caractere], 0) + 1
            continue
        if caractere in ESPACES:
            compte[ESPACES[caractere]] = compte.get(ESPACES[caractere], 0) + 1
            sortie.append(" ")
            continue
        sortie.append(caractere)
    texte = "".join(sortie)

    texte, corriges = _corriger_homoglyphes(texte)
    if corriges:
        compte["homoglyphe"] = corriges

    if normaliser:
        # NFC : « é » composé et « e + accent » se ressemblent et ne se
        # comparent pas. La forme composée est celle que produisent les
        # claviers et qu'attendent les moteurs de recherche.
        avant = texte
        texte = unicodedata.normalize("NFC", texte)
        if texte != avant:
            compte["normalisation NFC"] = 1

    if francais:
        texte = _espacement_francais(texte)

    return texte, compte


def _rapport(chemin: str, compte: dict[str, int]) -> str:
    if not compte:
        return f"{chemin} : propre"
    detail = ", ".join(f"{n} × {nom}" for nom, n in sorted(compte.items()))
    return f"{chemin} : {detail}"


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        description="Retire les marques invisibles d'un texte.")
    analyseur.add_argument("fichiers", nargs="*",
                           help="fichiers à traiter ; vide = entrée standard")
    analyseur.add_argument("--ecrire", action="store_true",
                           help="modifie les fichiers sur place")
    analyseur.add_argument("--verifier", action="store_true",
                           help="ne modifie rien ; code de sortie 1 si une marque est trouvée")
    analyseur.add_argument("--sans-liants", action="store_true",
                           help="retire aussi ZWJ et ZWNJ (signifiants en arabe, hébreu, indien)")
    analyseur.add_argument("--fr", action="store_true",
                           help="rétablit les insécables de la typographie française")
    analyseur.add_argument("--sans-nfc", action="store_true",
                           help="n'applique pas la normalisation NFC")
    options = analyseur.parse_args(argv)

    if not options.fichiers:
        texte, compte = nettoyer(sys.stdin.read(), options.sans_liants,
                                 options.fr, not options.sans_nfc)
        if options.verifier:
            print(_rapport("(entrée standard)", compte), file=sys.stderr)
            return 1 if compte else 0
        sys.stdout.write(texte)
        return 0

    trouve = False
    for nom in options.fichiers:
        chemin = Path(nom)
        try:
            origine = chemin.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"{nom} : illisible ({exc})", file=sys.stderr)
            continue
        texte, compte = nettoyer(origine, options.sans_liants,
                                 options.fr, not options.sans_nfc)
        if compte:
            trouve = True
        print(_rapport(nom, compte))
        # L'écriture n'a lieu que si le contenu change VRAIMENT : réécrire
        # un fichier identique modifie sa date et pollue un dépôt.
        if options.ecrire and not options.verifier and texte != origine:
            chemin.write_text(texte, encoding="utf-8")

    return 1 if (options.verifier and trouve) else 0


if __name__ == "__main__":
    raise SystemExit(main())
