"""Tests des modules 3 et 4. `python3 tests/test_rapport.py`"""
import sys, tempfile, os, json, zipfile
from pathlib import Path
from xml.dom.minidom import parseString

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db, personne as P, seance as S, resultat_test as RT
import rapport as R, export_docx as X, questionnaire as Q

BASE = PID = SID = None


def setup():
    global BASE, PID, SID
    BASE = tempfile.mktemp(suffix=".db")
    db.initialiser(BASE)
    PID = P.creer(P.Personne("J.L.", "adulte", "reconversion"), BASE).id
    SID = S.creer(S.Seance(PID, date="2026-09-16"), BASE).id


# ── Module 3 ───────────────────────────────────────────────────────────────
def t_resultat_exige_une_seance():
    try:
        RT.creer(RT.ResultatTest("seance-inexistante", "valeurs"), BASE)
    except ValueError:
        return
    raise AssertionError("résultat orphelin accepté")


def t_test_externe_sans_synthese_refuse():
    try:
        RT.creer(RT.ResultatTest(SID, "riasec_externe"), BASE)
    except ValueError:
        return
    raise AssertionError("test externe enregistré sans synthèse")


def t_reponses_json_aller_retour():
    r = RT.creer(RT.ResultatTest(SID, "valeurs", reponses={"v1": 4, "v2": 2}), BASE)
    relu = [x for x in RT.lister_par_seance(SID, BASE) if x.id == r.id][0]
    assert relu.reponses == {"v1": 4, "v2": 2}


def t_aucun_questionnaire_livre():
    """Le contenu Investigation n'a pas été fourni : rien n'est inventé."""
    assert Q.disponibles() == {}


def t_questionnaire_valide_et_totalise():
    d = Path(tempfile.mkdtemp())
    (d / "essai.json").write_text(json.dumps({
        "cle": "essai", "titre": "Essai",
        "items": [{"id": "a", "texte": "A", "categorie": "X"},
                  {"id": "b", "texte": "B", "categorie": "X"},
                  {"id": "c", "texte": "C", "categorie": "Y"}],
        "echelle": {"min": 1, "max": 5}}, ensure_ascii=False), encoding="utf-8")
    q = Q.disponibles(d)["essai"]
    assert q.categories == ["X", "Y"]
    assert Q.totaux_par_categorie(q, {"a": 3, "b": 4, "c": 5}) == {"X": 7, "Y": 5}


def t_questionnaire_invalide_rejete():
    d = Path(tempfile.mkdtemp())
    (d / "ko.json").write_text('{"cle":"k","titre":"K","items":[{"id":"a","texte":"A"},'
                               '{"id":"a","texte":"B"}]}', encoding="utf-8")
    try:
        Q.disponibles(d)
    except Q.QuestionnaireInvalide:
        return
    raise AssertionError("identifiants en double acceptés")


# ── Module 4 ───────────────────────────────────────────────────────────────
def t_les_quatre_blocs_existent():
    assert R.BLOCS == ("bloc_situation", "bloc_tests_utilises",
                       "bloc_resultats", "bloc_solutions")
    for pub in P.PUBLICS:
        assert set(R.intitules(pub)) == set(R.BLOCS), f"intitulés incomplets : {pub}"


def t_bloc_outils_prerempli_depuis_la_base():
    RT.creer(RT.ResultatTest(SID, "assessfirst_externe",
                             synthese_texte="Profil coordinateur"), BASE)
    rap = R.preparer(SID, BASE)
    assert "AssessFirst" in rap.bloc_tests_utilises
    assert "bloc_situation" in rap.blocs_vides, "les autres blocs ne sont pas générés"


def t_rapport_sans_seance_refuse():
    try:
        R.enregistrer(R.Rapport("seance-inexistante"), BASE)
    except ValueError:
        return
    raise AssertionError("rapport orphelin enregistré")


def t_rapport_relu_apres_enregistrement():
    rap = R.preparer(SID, BASE)
    rap.bloc_situation = "Reconversion après sept ans dans le médico-social."
    R.enregistrer(rap, BASE)
    relu = R.lire_par_seance(SID, BASE)
    assert relu.bloc_situation.startswith("Reconversion")


def t_docx_produit_et_valide():
    pers, sea = P.lire(PID, BASE), S.lire(SID, BASE)
    rap = R.preparer(SID, BASE)
    rap.bloc_solutions = "- Contacter Cap emploi\n- Ouvrir un dossier VAE"
    chemin = X.exporter(pers, sea, rap, tempfile.mkdtemp())
    with zipfile.ZipFile(chemin) as z:
        assert z.testzip() is None
        xml = z.read("word/document.xml").decode("utf-8")
        parseString(xml)
        assert "Cap emploi" in xml and "Ouvrir un dossier VAE" in xml


def t_nom_de_fichier_sans_nom_complet():
    pers = P.Personne("K.M.", "adulte", "vae", nom_complet="Jean Dupont")
    nom = X.nom_fichier(pers, S.Seance(pers.id, date="2026-09-16"))
    assert "Dupont" not in nom and "Jean" not in nom and "K-M" in nom


def t_aucune_mention_reglementaire_inventee():
    """Ni numéro d'agrément, ni visa des articles du code du travail."""
    import config
    texte = " ".join(str(v) for v in config.ORGANISATION.values())
    texte += config.TITRE_DOCUMENT + config.SOUS_TITRE + config.AVERTISSEMENT
    for interdit in ("R6313", "QUALIOPI", "Qualiopi", "DIRECCTE", "SIRET"):
        assert interdit not in texte, f"mention réglementaire présente : {interdit}"


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
