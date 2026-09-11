# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  Du fichier de sauvegarde au PDF.

  Le programme de secrétariat produit un fichier bereshit-AAAA-MM-JJ.json.
  Ce module le lit et en tire la planche à tracer, sans ressaisie :

      python depuis_sauvegarde.py bereshit-2026-09-11.json

  ► LES RÈGLES D'ÉCRITURE SONT ÉCRITES DEUX FOIS — ici en Python, et
    dans loge/lib/formules.js en JavaScript. C'est un risque réel : deux
    implémentations d'une même règle finissent par diverger. La
    référence est formules.js ; verifier_accord.py compare les deux et
    échoue si elles ne disent plus la même chose.
═══════════════════════════════════════════════════════════════════════
"""

import json
import sys
from datetime import date
from pathlib import Path

from planche_rbi import construire

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

DEGRES = {1: "Apprenti Oved", 2: "Compagnon Boneh", 3: "Maître Adon"}
DE     = {1: "d'Apprenti Oved", 2: "de Compagnon Boneh", 3: "de Maître Adon"}
RANGS  = {1: "premier", 2: "deuxième", 3: "troisième"}
OFFICES = {"venerable": "Vénérable Maître",
           "premier_surveillant": "Premier Surveillant",
           "second_surveillant": "Second Surveillant"}


# ── Les règles du Rite, doublées de formules.js ────────────────────
def avl(annee):
    """An de Vraie Lumière : année hébraïque, Constitution V9."""
    return annee + 3760


def pierre_plate(euros):
    """Le kilogramme vaut l'euro, le gramme le centime."""
    centimes = round(euros * 100)
    kg, g = divmod(centimes, 100)
    return f"{kg} kg" if g == 0 else f"{kg} kg {g * 10:03d}"


def mois_maconnique(d):
    """Mars = 1er mois. NON CONFIRMÉ par le Rite."""
    return (d.month + 9) % 12 + 1


def date_longue(iso):
    d = date.fromisoformat(iso)
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"


def qualite(m):
    """Degré du Rite d'abord, à défaut celui de l'Ordre et la dignité."""
    if m.get("degre"):
        return f"{DEGRES[m['degre']]} du Rite Brith Israël"
    if m.get("grade"):
        q = f"{m['grade']} du Rite Brith Israël"
        return q + (", " + m["dignite"] if m.get("dignite") else "")
    return m.get("qualite") or ""


def presence(E, m):
    """Un excusé permanent l'est d'office, sans qu'on l'ait coché."""
    p = (E.get("presences") or {}).get(str(m["id"]))
    if p:
        return p
    return "excuse" if m.get("excusePermanent") else "attendu"


def personne(m):
    d = {"nom": f"{m['prenoms']} {m['nom']}".strip(), "qualite": qualite(m)}
    if m.get("office"):
        d["office"] = OFFICES.get(m["office"], m["office"])
    elif m.get("excusePermanent") and m.get("motifExcuse"):
        d["office"] = m["motifExcuse"]
    return d


def titulaire(E, code):
    for m in E["membres"]:
        if m.get("office") == code:
            return f"{m['prenoms']} {m['nom']}".strip()
    return "…"


def convertir(paquet, tronc_euros=0.0):
    """Du modèle du programme de secrétariat à celui de la planche."""
    if paquet.get("_format") != "gestion-loge-rbi":
        raise ValueError("Ce fichier n'est pas une sauvegarde de la gestion de Loge.")
    E = paquet["donnees"]
    T = E["tenue"]
    d = date.fromisoformat(T["date"])
    rang = lambda m: m.get("rangProtocole") or 99

    convocables = [m for m in E["membres"] if m["statut"] in ("actif", "honoraire")]
    convocables.sort(key=rang)
    presents = [personne(m) for m in convocables if presence(E, m) == "present"]
    excuses  = [personne(m) for m in convocables if presence(E, m) == "excuse"]

    visiteurs = []
    for v in E.get("visiteurs", []):
        if not v.get("presentTenue"):
            continue
        lieu = v.get("loge") or ""
        if v.get("orient"):
            lieu += f" à l'O∴ de {v['orient']}"
        if v.get("obedience"):
            lieu += f" — {v['obedience']}"
        d_v = {"nom": f"{v.get('prenom','')} {v.get('nom','')}".strip(),
               "qualite": ", ".join(x for x in (v.get("grade"), lieu.strip()) if x)}
        if v.get("tuilePar"):
            d_v["office"] = f"tuilé par {v['tuilePar']}"
        visiteurs.append(d_v)

    degre = int(T.get("degre") or 1)
    return {
        "loge": {"nom": "BERESHIT", "numero": "00", "nom_hebreu": "בראשית",
                 "orient": "l'Alliance",
                 "mention": "Loge Mère du Rite — Atelier Mixte à l'O∴ de l'Alliance"},
        "date_longue": date_longue(T["date"]),
        "avl": avl(d.year), "jour": d.day, "mois": mois_maconnique(d),
        "lieu": f"{T.get('lieuNom','')}, à {T.get('lieuVille','')}".strip(", "),
        "degre_ordinal": RANGS[degre], "degre_de": DE[degre],
        "venerable": titulaire(E, "venerable"),
        "presents": presents, "excuses": excuses, "visiteurs": visiteurs,
        # L'ordre du jour donne les intitulés ; le récit reste à écrire.
        "paragraphes": [{"intitule": o["t"], "texte": ""}
                        for o in E.get("odj", []) if o.get("t", "").strip()],
        "sac": "revient pur et sans attaches",
        "tronc": pierre_plate(tronc_euros),
        "tronc_confie_a": "F∴ Second Surveillant",
        "prochaine": "…",
        "redacteur": "…",
        "signatures": [(OFFICES[c], titulaire(E, c))
                       for c in ("venerable", "premier_surveillant", "second_surveillant")],
    }


def principal(argv):
    if len(argv) < 2:
        print(__doc__)
        print("usage : python depuis_sauvegarde.py <sauvegarde.json> [tronc_en_euros]")
        return 1
    source = Path(argv[1])
    tronc = float(argv[2].replace(",", ".")) if len(argv) > 2 else 0.0
    paquet = json.loads(source.read_text(encoding="utf-8"))
    donnees = convertir(paquet, tronc)
    sortie = source.with_name(f"planche-{paquet['donnees']['tenue']['date']}.pdf")
    chemin, heb = construire(donnees, sortie)
    print("PDF produit :", chemin)
    print(f"  {len(donnees['presents'])} présents · {len(donnees['excuses'])} excusés "
          f"· {len(donnees['visiteurs'])} visiteur(s)")
    if not heb:
        print("  hébreu omis : aucune police hébraïque sur cette machine")
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv))
