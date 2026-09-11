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

ANNEES = [2024, 2025, 2026, 2030, 2100]
MONTANTS = [0, 0.05, 0.5, 1, 12.30, 87.5, 87.05, 100, 1234.99]
DATES = ["2026-01-15", "2026-03-01", "2026-03-31", "2026-07-14",
         "2026-09-07", "2026-12-31"]


def cote_javascript():
    script = f"""
import {{ avl, pierrePlate, moisMaconnique }} from '{FORMULES.as_uri()}';
const annees = {json.dumps(ANNEES)};
const montants = {json.dumps(MONTANTS)};
const dates = {json.dumps(DATES)};
console.log(JSON.stringify({{
  avl: annees.map(avl),
  pierre: montants.map(pierrePlate),
  mois: dates.map(d => moisMaconnique(new Date(d + 'T12:00:00')))
}}));
"""
    r = subprocess.run(["node", "--input-type=module", "-e", script],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("le côté JavaScript n'a pas répondu :\n" + r.stderr)
    return json.loads(r.stdout)


def cote_python():
    return {
        "avl": [py.avl(a) for a in ANNEES],
        "pierre": [py.pierre_plate(m) for m in MONTANTS],
        "mois": [py.mois_maconnique(date.fromisoformat(d)) for d in DATES],
    }


def principal():
    js, pyt = cote_javascript(), cote_python()
    desaccords = []
    intitules = {"avl": "An de Vraie Lumière", "pierre": "pierre plate du Tronc",
                 "mois": "mois maçonnique"}
    entrees = {"avl": ANNEES, "pierre": MONTANTS, "mois": DATES}
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
