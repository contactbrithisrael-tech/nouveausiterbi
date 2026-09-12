# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  Les règles du Rite sont écrites deux fois : en JavaScript dans
  loge/lib/formules.js, dont se sert le programme de secrétariat, et en
  Python dans depuis_sauvegarde.py, dont se sert la sortie PDF.

  Deux implémentations d'une même règle finissent par diverger, et la
  divergence ne se voit pas : elle sort imprimée sur une planche à
  tracer, des mois plus tard.

  Ce fichier les fait s'affronter sur les mêmes entrées. La référence
  est formules.js. Si elles ne disent plus la même chose, il échoue.

  Le calendrier hébraïque y est le point sensible : d'un côté celui du
  navigateur, de l'autre une bibliothèque Python. Deux implémentations
  entièrement étrangères l'une à l'autre — leur accord vaut donc mieux
  qu'un contrôle de moi contre moi-même.

      python verifier_accord.py
═══════════════════════════════════════════════════════════════════════
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import depuis_sauvegarde as py

FORMULES = Path(__file__).resolve().parent.parent / "lib" / "formules.js"

MONTANTS = [0, 0.05, 0.5, 1, 12.30, 87.5, 87.05, 100, 1234.99]
# Des dates choisies pour éprouver le calendrier : la veille et le jour
# de Roch Hachana, une année embolismique et ses deux Adar, un 29 février.
DATES = ["2026-01-15", "2026-09-07", "2026-09-11", "2026-09-12",
         "2026-10-05", "2026-12-31", "2027-03-01", "2027-03-20",
         "2028-02-29", "2030-06-15"]


def cote_javascript():
    script = f"""
import {{ dateHebraique, anneeHebraique, pierrePlate }} from '{FORMULES.as_uri()}';
const montants = {json.dumps(MONTANTS)};
const dates = {json.dumps(DATES)};
const D = s => new Date(s + 'T12:00:00Z');
console.log(JSON.stringify({{
  hebreu: dates.map(d => dateHebraique(D(d))),
  annee:  dates.map(d => anneeHebraique(D(d))),
  pierre: montants.map(pierrePlate)
}}));
"""
    r = subprocess.run(["node", "--input-type=module", "-e", script],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("le côté JavaScript n'a pas répondu :\n" + r.stderr)
    return json.loads(r.stdout)


def cote_python():
    return {
        "hebreu": [py.date_hebraique(date.fromisoformat(d)) for d in DATES],
        "annee":  [py.annee_hebraique(date.fromisoformat(d)) for d in DATES],
        "pierre": [py.pierre_plate(m) for m in MONTANTS],
    }


def principal():
    js, pyt = cote_javascript(), cote_python()
    desaccords = []
    intitules = {"hebreu": "date hébraïque complète",
                 "annee":  "année hébraïque",
                 "pierre": "pierre plate du Tronc"}
    entrees = {"hebreu": DATES, "annee": DATES, "pierre": MONTANTS}
    for cle, titre in intitules.items():
        for e, a, b in zip(entrees[cle], js[cle], pyt[cle]):
            if a != b:
                desaccords.append(f"{titre} · {e} : JavaScript dit {a!r}, Python dit {b!r}")
        print(f"  {'✓' if js[cle] == pyt[cle] else '✗'} {titre} "
              f"({len(entrees[cle])} cas)")
    if desaccords:
        print("\n  LES DEUX CÔTÉS ONT DIVERGÉ :")
        for d in desaccords:
            print("   ", d)
        return 1
    print("\n  les deux implémentations disent la même chose")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
