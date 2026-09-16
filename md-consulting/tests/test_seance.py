"""Tests du Module 2. `python3 tests/test_seance.py`"""
import sys, tempfile, os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db, personne as P, seance as S

BASE = None
PID = None
DEBUT = datetime(2026, 9, 16, 10, 0, 0)


def setup():
    global BASE, PID
    BASE = tempfile.mktemp(suffix=".db")
    db.initialiser(BASE)
    PID = P.creer(P.Personne("Dupont", "Jean", "adulte", "reconversion"), BASE).id


def _demarree() -> S.Seance:
    s = S.Seance(PID)
    s.demarrer(DEBUT)
    return s


def t_seance_exige_une_personne_existante():
    try:
        S.creer(S.Seance("identifiant-inexistant"), BASE)
    except ValueError:
        return
    raise AssertionError("une séance orpheline a été créée")


def t_chrono_non_demarre():
    s = S.Seance(PID)
    assert s.etat() == S.NON_DEMARREE and s.minutes_ecoulees() is None


def t_chrono_seuils():
    s = _demarree()
    assert s.etat(DEBUT + timedelta(minutes=10)) == S.EN_COURS
    assert s.etat(DEBUT + timedelta(minutes=79)) == S.EN_COURS
    assert s.etat(DEBUT + timedelta(minutes=80)) == S.VIGILANCE   # 10 min avant 90
    assert s.etat(DEBUT + timedelta(minutes=90)) == S.DEPASSEMENT
    assert s.etat(DEBUT + timedelta(minutes=200)) == S.DEPASSEMENT


def t_chrono_survit_au_rechargement():
    """Le départ est relu en base : une page rechargée ne remet pas à zéro."""
    s = S.creer(_demarree(), BASE)
    relue = S.lire(s.id, BASE)
    assert relue.heure_debut == "10:00:00"
    assert int(relue.minutes_ecoulees(DEBUT + timedelta(minutes=42))) == 42


def t_demarrer_est_sans_effet_si_deja_demarree():
    s = _demarree()
    s.demarrer(DEBUT + timedelta(hours=3))
    assert s.heure_debut == "10:00:00", "le départ a été réécrit"


def t_horloge_avant_le_depart_ne_donne_pas_de_negatif():
    s = _demarree()
    assert s.minutes_ecoulees(DEBUT - timedelta(minutes=30)) == 0.0


def t_plafond_personnalisable():
    s = S.Seance(PID, chrono_max_minutes=60)
    s.demarrer(DEBUT)
    assert s.etat(DEBUT + timedelta(minutes=61)) == S.DEPASSEMENT
    assert S.libelle_chrono(s, DEBUT + timedelta(minutes=61)) == "61 min / 60 min"


def t_duree_max_nulle_refusee():
    try:
        S.creer(S.Seance(PID, chrono_max_minutes=0), BASE)
    except ValueError:
        return
    raise AssertionError("durée maximale nulle acceptée")


def t_suppression_personne_emporte_les_seances():
    pid = P.creer(P.Personne("Martin", "Léa", "adulte", "vae"), BASE).id
    S.creer(S.Seance(pid), BASE)
    assert len(S.lister_par_personne(pid, BASE)) == 1
    P.supprimer(pid, BASE)
    assert S.lister_par_personne(pid, BASE) == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    setup()
    echecs = 0
    for t in tests:
        try:
            t(); print(f"  OK   {t.__name__}")
        except Exception as exc:
            echecs += 1; print(f"  ÉCHEC {t.__name__} : {exc}")
    os.path.exists(BASE) and os.remove(BASE)
    print(f"\n{len(tests) - echecs}/{len(tests)} tests passés")
    sys.exit(1 if echecs else 0)
