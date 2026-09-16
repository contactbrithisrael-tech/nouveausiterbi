"""Tests de la fiche Personne. `python3 tests/test_personne.py`"""
import sys, tempfile, os
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db, personne as P

BASE = None


def setup():
    global BASE
    BASE = tempfile.mktemp(suffix=".db")
    db.initialiser(BASE)


def _ne_le(annees: int) -> str:
    return (date.today() - timedelta(days=int(annees * 365.25) + 1)).isoformat()


def _adulte(nom="Dupont", prenom="Jean", **extra) -> P.Personne:
    return P.Personne(nom, prenom, "adulte", "reconversion",
                      date_naissance=_ne_le(36), telephone="0600000000",
                      adresse="1 rue du Port", situation="Cadre", **extra)


# ── Identité ───────────────────────────────────────────────────────────────
def t_nom_et_prenom_obligatoires():
    for nom, prenom in (("", "Jean"), ("Dupont", "  ")):
        try:
            P.creer(P.Personne(nom, prenom, "adulte", "reconversion"), BASE)
        except P.DonneesInvalides:
            continue
        raise AssertionError(f"fiche acceptée sans nom ou prénom : {nom!r}/{prenom!r}")


def t_identifiant_reste_un_uuid():
    p = P.creer(_adulte(), BASE)
    assert len(p.id) == 36 and p.nom not in p.id and p.prenom not in p.id


def t_nom_affiche():
    assert P.Personne("Dupont", "Jean", "adulte", "vae").nom_affiche == "DUPONT Jean"


def t_fiche_relue_entierement():
    p = _adulte("Martin", "Léa", courriel="lea@exemple.fr", rqth=True,
                lien_mescompetences="https://mescompetences.info/x",
                notes_libres="Reçue en septembre.")
    P.creer(p, BASE)
    r = P.lire(p.id, BASE)
    assert (r.nom, r.prenom, r.courriel, r.rqth) == ("Martin", "Léa",
                                                     "lea@exemple.fr", True)
    assert r.adresse == "1 rue du Port" and r.notes_libres == "Reçue en septembre."


# ── Âge et minorité ────────────────────────────────────────────────────────
def t_age_calcule_depuis_la_naissance():
    assert P.age_au(_ne_le(13)) == 13
    assert P.age_au(None) is None


def t_age_exact_prime_sur_la_tranche():
    """Une tranche mal saisie ne doit pas faire passer un mineur pour un adulte."""
    p = P.Personne("Martin", "Léa", "adulte", "lycee", date_naissance=_ne_le(16))
    assert p.is_mineur and p.consentement_requis


def t_naissance_future_refusee():
    demain = (date.today() + timedelta(days=1)).isoformat()
    try:
        P.creer(P.Personne("Dupont", "Jean", "adulte", "vae",
                           date_naissance=demain), BASE)
    except P.DonneesInvalides:
        return
    raise AssertionError("date de naissance future acceptée")


def t_sans_date_de_naissance_on_retombe_sur_la_tranche():
    p = P.Personne("Martin", "Léa", "college", "college")
    assert p.age is None and p.consentement_requis


# ── Consentement parental ──────────────────────────────────────────────────
def t_mineur_sans_consentement_bloque():
    p = P.Personne("Martin", "Léa", "college", "college", date_naissance=_ne_le(13))
    try:
        P.creer(p, BASE)
    except P.ConsentementParentalManquant as exc:
        assert "13 ans" in str(exc), "l'âge exact devrait figurer dans le message"
        assert P.lire(p.id, BASE) is None, "rien ne doit être écrit en base"
        return
    raise AssertionError("la création aurait dû être bloquée")


def t_mineur_avec_consentement_passe():
    p = P.Personne("Petit", "Tom", "lycee", "lycee", date_naissance=_ne_le(16),
                   consentement_parental_date=date.today().isoformat(),
                   representant_legal="Petit Marie", representant_contact="0600000000")
    P.creer(p, BASE)
    assert P.lire(p.id, BASE).consentement_ok


def t_modification_ne_peut_pas_retirer_le_consentement():
    hier = (date.today() - timedelta(days=1)).isoformat()
    p = P.Personne("Roux", "Ana", "lycee", "lycee", date_naissance=_ne_le(16),
                   consentement_parental_date=hier)
    P.creer(p, BASE)
    p.consentement_parental_date = None
    try:
        P.modifier(p, BASE)
    except P.ConsentementParentalManquant:
        assert P.lire(p.id, BASE).consentement_parental_date == hier
        return
    raise AssertionError("retirer le consentement d'un mineur aurait dû être bloqué")


def t_date_consentement_invalide_rejetee():
    try:
        P.creer(P.Personne("Roux", "Ana", "college", "college",
                           consentement_parental_date="10/09/2026"), BASE)
    except P.DonneesInvalides:
        return
    raise AssertionError("format de date invalide accepté")


def t_adulte_sans_consentement_passe():
    p = P.creer(_adulte("Blanc", "Éric"), BASE)
    assert not P.lire(p.id, BASE).consentement_requis


def t_seuil_verrouille_a_dix_huit_ans():
    """Décision de Mickael : consentement parental obligatoire pour tout mineur.
    Ce test existe pour que le seuil ne redescende pas sans qu'on s'en aperçoive."""
    assert P.SEUIL_CONSENTEMENT_PARENTAL == 18


def t_consentement_exige_a_dix_sept_ans():
    p = P.Personne("Fort", "Noé", "lycee", "lycee", date_naissance=_ne_le(17))
    assert p.consentement_requis, "un jeune de 17 ans doit exiger le consentement"


def t_pas_de_consentement_a_dix_huit_ans():
    p = P.Personne("Fort", "Zoé", "adulte", "reconversion", date_naissance=_ne_le(18))
    assert not p.consentement_requis


# ── Complétude ─────────────────────────────────────────────────────────────
def t_fiche_complete_detectee():
    p = _adulte("Noir", "Paul")
    assert p.fiche_complete, p.champs_manquants


def t_champs_manquants_listes():
    p = P.Personne("Vert", "Luc", "adulte", "vae")
    manquants = p.champs_manquants
    assert "date de naissance" in manquants and "adresse" in manquants
    assert "téléphone ou courriel" in manquants


def t_un_seul_contact_suffit():
    p = _adulte("Gris", "Iris")
    p.telephone = None
    p.courriel = "iris@exemple.fr"
    assert "téléphone ou courriel" not in p.champs_manquants


def t_mineur_doit_renseigner_son_representant():
    p = P.Personne("Bleu", "Zoé", "lycee", "lycee", date_naissance=_ne_le(16),
                   consentement_parental_date=date.today().isoformat(),
                   adresse="2 rue Haute", situation="1re", telephone="0600000000")
    assert "représentant légal" in p.champs_manquants


def t_incompletude_ne_bloque_pas_l_enregistrement():
    p = P.Personne("Jaune", "Max", "adulte", "vae")
    P.creer(p, BASE)
    assert P.lire(p.id, BASE) is not None and not p.fiche_complete


# ── Recherche et suppression ───────────────────────────────────────────────
def t_recherche_par_nom_prenom_courriel():
    P.creer(_adulte("Orange", "Nina", courriel="nina@exemple.fr"), BASE)
    assert len(P.lister(recherche="Orange", chemin=BASE)) == 1
    assert len(P.lister(recherche="Nina", chemin=BASE)) == 1
    assert len(P.lister(recherche="nina@exemple", chemin=BASE)) == 1


def t_suppression_cascade():
    import uuid
    p = P.creer(_adulte("Rose", "Ugo"), BASE)
    sid = str(uuid.uuid4())
    with db.connexion(BASE) as cx:
        cx.execute("INSERT INTO seance (id, personne_id, date) VALUES (?,?,?)",
                   (sid, p.id, "2026-09-16"))
        cx.execute("INSERT INTO resultat_test (id, seance_id, type_test, date_saisie) "
                   "VALUES (?,?,?,?)", (str(uuid.uuid4()), sid, "valeurs", "2026-09-16"))
    assert P.compter_liees(p.id, BASE)["seances"] == 1
    assert P.supprimer(p.id, BASE) is True
    with db.connexion(BASE) as cx:
        assert cx.execute("SELECT COUNT(*) FROM resultat_test WHERE seance_id = ?",
                          (sid,)).fetchone()[0] == 0


# ── Migration depuis l'ancienne fiche ──────────────────────────────────────
def t_migration_conserve_les_donnees():
    import sqlite3
    ancien = tempfile.mktemp(suffix=".db")
    cx = sqlite3.connect(ancien)
    cx.executescript("""
        CREATE TABLE personne (id TEXT PRIMARY KEY, pseudonyme TEXT NOT NULL,
          nom_complet TEXT, tranche_age TEXT NOT NULL, public TEXT NOT NULL,
          consentement_parental_date TEXT, lien_mescompetences TEXT,
          notes_libres TEXT, date_creation TEXT NOT NULL);
        INSERT INTO personne VALUES ('u1','J.L.','Jean Lerat','adulte','reconversion',
          NULL,NULL,'une note','2026-09-01');""")
    cx.commit(); cx.close()
    db.initialiser(ancien)
    r = P.lire("u1", ancien)
    assert r.nom == "Jean Lerat" and r.prenom == ""
    assert r.notes_libres == "une note", "les notes doivent survivre à la migration"
    assert "prénom" in r.champs_manquants, "le prénom manquant doit être signalé"
    os.remove(ancien)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    setup()
    echecs = 0
    for t in tests:
        try:
            t(); print(f"  OK   {t.__name__}")
        except Exception as exc:
            echecs += 1; print(f"  ÉCHEC {t.__name__} : {type(exc).__name__} {exc}")
    os.path.exists(BASE) and os.remove(BASE)
    print(f"\n{len(tests) - echecs}/{len(tests)} tests passés")
    sys.exit(1 if echecs else 0)
