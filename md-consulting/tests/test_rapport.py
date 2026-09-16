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
    PID = P.creer(P.Personne("Lerat", "Jean", "adulte", "reconversion"), BASE).id
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


def t_questionnaire_invalide_rejete():
    d = Path(tempfile.mkdtemp())
    (d / "ko.json").write_text(
        '{"cle":"k","titre":"K","forme":"checklist","items":'
        '[{"id":"a","texte":"A"},{"id":"a","texte":"B"}]}', encoding="utf-8")
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


def t_les_quatre_blocs_sont_assembles_seuls():
    RT.creer(RT.ResultatTest(SID, "assessfirst_externe",
                             synthese_texte="Profil coordinateur"), BASE)
    rap = R.preparer(SID, BASE)
    assert rap.blocs_vides == [], f"blocs encore vides : {rap.blocs_vides}"
    assert "AssessFirst" in rap.bloc_tests_utilises
    assert "Profil coordinateur" in rap.bloc_resultats


def t_situation_reprend_la_fiche_et_l_objectif():
    pers = P.lire(PID, BASE)
    sea = S.lire(SID, BASE)
    sea.objectif_texte = "Clarifier deux pistes."
    S.modifier(sea, BASE)
    texte = R.composer_situation(pers, S.lire(SID, BASE))
    assert pers.nom.upper() in texte and P.PUBLICS[pers.public] in texte
    assert "Clarifier deux pistes." in texte
    assert "90 minutes" in texte


def t_solutions_reprennent_demarches_et_ressources():
    import questionnaire as Q
    import ressources as Rs
    RT.creer(RT.ResultatTest(SID, "points_forts",
                             synthese_texte="Points forts — 2 retenus"), BASE)
    pers = P.lire(PID, BASE)
    texte = R.composer_solutions(pers, SID, BASE)
    suite = Q.disponibles()["points_forts"].get("suite", [])[0]
    assert suite in texte, "les démarches prévues par l'outil manquent"
    noms = [r.nom for r in Rs.pour_public(pers.public)]
    assert all(n in texte for n in noms), "des ressources du public manquent"


def t_le_compte_rendu_ne_reprend_pas_la_mise_en_garde_du_consultant():
    """MISES_EN_GARDE s'adresse au consultant : ce texte n'a rien à faire
    dans un document remis à la personne."""
    import ressources as Rs
    pid = P.creer(P.Personne("Blanc", "Eve", "adulte", "burnout"), BASE).id
    sid = S.creer(S.Seance(pid), BASE).id
    rap = R.preparer(sid, BASE)
    entier = " ".join(getattr(rap, b) for b in R.BLOCS)
    garde = Rs.MISES_EN_GARDE["burnout"].replace("**", "")
    assert garde not in entier, "la mise en garde du consultant est dans le document"
    assert "demande expresse du consultant" not in entier
    attendu = Rs.ORIENTATIONS_BENEFICIAIRE["burnout"]
    assert attendu in rap.bloc_solutions, "l'orientation de la personne manque"


def t_un_outil_donnee_de_sante_n_apparait_jamais():
    """Rien n'est enregistré du CBI : il ne peut donc rien apporter au rapport."""
    import questionnaire as Q
    pid = P.creer(P.Personne("Noir", "Luc", "adulte", "burnout"), BASE).id
    sid = S.creer(S.Seance(pid), BASE).id
    rap = R.preparer(sid, BASE)
    entier = " ".join(getattr(rap, b) for b in R.BLOCS)
    titre = Q.disponibles()["cbi_epuisement"].titre
    assert titre not in entier, "le CBI apparaît dans le compte rendu"


def t_un_seul_compte_rendu_par_seance():
    """Deux versions pour une même séance laissaient la lecture choisir au
    hasard. La base l'interdit maintenant."""
    pid = P.creer(P.Personne("Gris", "Iris", "adulte", "vae"), BASE).id
    sid = S.creer(S.Seance(pid), BASE).id
    premier = R.preparer(sid, BASE)
    premier.bloc_situation = "Première version."
    R.enregistrer(premier, BASE)
    second = R.preparer(sid, BASE)          # identifiant différent
    second.bloc_situation = "Seconde version."
    R.enregistrer(second, BASE)
    with db.connexion(BASE) as cx:
        total = cx.execute("SELECT COUNT(*) FROM rapport WHERE seance_id = ?",
                           (sid,)).fetchone()[0]
    assert total == 1, f"{total} comptes rendus pour une séance"
    assert R.lire_par_seance(sid, BASE).bloc_situation == "Seconde version."


def t_migration_ne_garde_que_le_dernier_compte_rendu():
    import sqlite3, tempfile as tf
    ancien = tf.mktemp(suffix=".db")
    cx = sqlite3.connect(ancien)
    cx.executescript("""
        CREATE TABLE seance (id TEXT PRIMARY KEY, personne_id TEXT, date TEXT);
        CREATE TABLE rapport (id TEXT PRIMARY KEY, seance_id TEXT NOT NULL,
          date_generation TEXT NOT NULL, bloc_situation TEXT,
          bloc_tests_utilises TEXT, bloc_resultats TEXT, bloc_solutions TEXT,
          export_docx_path TEXT);
        INSERT INTO seance VALUES ('s1','p1','2026-09-16');
        INSERT INTO rapport VALUES ('r1','s1','2026-09-16T10:00:00','vieux',
          NULL,NULL,NULL,NULL);
        INSERT INTO rapport VALUES ('r2','s1','2026-09-16T11:00:00','recent',
          NULL,NULL,NULL,NULL);""")
    cx.commit(); cx.close()
    db.initialiser(ancien)
    with db.connexion(ancien) as cx:
        lignes = cx.execute("SELECT bloc_situation FROM rapport").fetchall()
    assert [l[0] for l in lignes] == ["recent"], lignes
    os.remove(ancien)


def t_reassemblage_ecrase_les_retouches():
    rap = R.preparer(SID, BASE)
    rap.bloc_situation = "Texte écrit à la main."
    R.enregistrer(rap, BASE)
    assert R.lire_par_seance(SID, BASE).bloc_situation == "Texte écrit à la main."
    R.enregistrer(R.regenerer(rap, BASE), BASE)
    relu = R.lire_par_seance(SID, BASE)
    assert "Texte écrit à la main." not in relu.bloc_situation
    assert P.lire(PID, BASE).nom.upper() in relu.bloc_situation


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


def t_nom_de_fichier_lisible():
    pers = P.Personne("Dupont", "Jean", "adulte", "vae")
    nom = X.nom_fichier(pers, S.Seance(pers.id, date="2026-09-16"))
    assert nom == "2026-09-16_Dupont-Jean_compte-rendu.docx", nom


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
