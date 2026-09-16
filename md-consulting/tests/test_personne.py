"""Tests du Module 1. Aucune dépendance externe : `python3 tests/test_personne.py`."""
import sys, tempfile, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db, personne as P

BASE = None


def setup():
    global BASE
    BASE = tempfile.mktemp(suffix=".db")
    db.initialiser(BASE)


def teardown():
    if BASE and os.path.exists(BASE):
        os.remove(BASE)


def t_mineur_sans_consentement_bloque():
    p = P.Personne(pseudonyme="A.B.", tranche_age="college", public="college")
    try:
        P.creer(p, BASE)
    except P.ConsentementParentalManquant:
        assert P.lire(p.id, BASE) is None, "rien ne doit être écrit en base"
        return
    raise AssertionError("la création aurait dû être bloquée")


def t_mineur_avec_consentement_passe():
    p = P.Personne("C.D.", "lycee", "lycee", consentement_parental_date="2026-09-10")
    P.creer(p, BASE)
    relu = P.lire(p.id, BASE)
    assert relu is not None and relu.is_mineur and relu.consentement_ok


def t_adulte_sans_consentement_passe():
    p = P.Personne("E.F.", "adulte", "reconversion")
    P.creer(p, BASE)
    relu = P.lire(p.id, BASE)
    assert relu is not None and not relu.is_mineur and not relu.consentement_requis


def t_nom_complet_separe_de_l_identifiant():
    p = P.Personne("G.H.", "adulte", "vae", nom_complet="Jean Dupont")
    P.creer(p, BASE)
    relu = P.lire(p.id, BASE)
    assert relu.nom_complet == "Jean Dupont" and p.id not in "Jean Dupont"
    assert len(p.id) == 36, "l'identifiant est un UUID, jamais le nom"


def t_modification_revalide_le_consentement():
    p = P.Personne("I.J.", "lycee", "lycee", consentement_parental_date="2026-09-10")
    P.creer(p, BASE)
    p.consentement_parental_date = None
    try:
        P.modifier(p, BASE)
    except P.ConsentementParentalManquant:
        assert P.lire(p.id, BASE).consentement_parental_date == "2026-09-10"
        return
    raise AssertionError("retirer le consentement d'un mineur aurait dû être bloqué")


def t_date_consentement_invalide_rejetee():
    p = P.Personne("K.L.", "college", "college", consentement_parental_date="10/09/2026")
    try:
        P.creer(p, BASE)
    except P.DonneesInvalides:
        return
    raise AssertionError("format de date invalide accepté")


def t_suppression_cascade():
    import uuid
    p = P.creer(P.Personne("M.N.", "adulte", "handicap"), BASE)
    sid, rid = str(uuid.uuid4()), str(uuid.uuid4())
    with db.connexion(BASE) as cx:
        cx.execute("INSERT INTO seance (id, personne_id, date) VALUES (?,?,?)",
                   (sid, p.id, "2026-09-16"))
        cx.execute("INSERT INTO resultat_test (id, seance_id, type_test, date_saisie) "
                   "VALUES (?,?,?,?)", (rid, sid, "valeurs", "2026-09-16"))
    assert P.compter_liees(p.id, BASE) == {"seances": 1, "tests": 1, "rapports": 0}
    assert P.supprimer(p.id, BASE) is True
    with db.connexion(BASE) as cx:
        assert cx.execute("SELECT COUNT(*) FROM seance").fetchone()[0] == 0
        assert cx.execute("SELECT COUNT(*) FROM resultat_test").fetchone()[0] == 0


def t_filtres_liste():
    P.creer(P.Personne("O.P.", "adulte", "vae", nom_complet="Zoe Martin"), BASE)
    assert all(x.public == "vae" for x in P.lister(public="vae", chemin=BASE))
    assert len(P.lister(recherche="Zoe", chemin=BASE)) == 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    setup()
    echecs = 0
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except Exception as exc:
            echecs += 1
            print(f"  ÉCHEC {t.__name__} : {exc}")
    teardown()
    print(f"\n{len(tests) - echecs}/{len(tests)} tests passés")
    sys.exit(1 if echecs else 0)
