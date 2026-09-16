"""Format d'affichage des dates. `python3 tests/test_dates.py`"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dates_fr


def t_date_simple():
    assert dates_fr.jour("2026-09-10") == "10/09/2026"


def t_horodatage():
    assert dates_fr.jour("2026-09-10T14:03:00") == "10/09/2026"
    assert dates_fr.jour_heure("2026-09-10T14:03:00") == "10/09/2026 à 14:03"


def t_valeur_absente():
    assert dates_fr.jour(None) == "—" and dates_fr.jour("") == "—"


def t_valeur_illisible_rendue_telle_quelle():
    assert dates_fr.jour("bientôt") == "bientôt"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    echecs = 0
    for t in tests:
        try:
            t(); print(f"  OK   {t.__name__}")
        except Exception as exc:
            echecs += 1; print(f"  ÉCHEC {t.__name__} : {exc}")
    print(f"\n{len(tests) - echecs}/{len(tests)} tests passés")
    sys.exit(1 if echecs else 0)
