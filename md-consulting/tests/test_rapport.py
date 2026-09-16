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


# ── Notes et affinités ─────────────────────────────────────────────────────
def t_croisement_note_affinite():
    import matieres as M
    seuil = M.SEUIL_REUSSITE
    cas = [
        (seuil + 1, M.AIME, M.APPUI),
        (seuil - 1, M.AIME, M.A_TRAVAILLER),
        (seuil + 1, M.REJET, M.SANS_ENVIE),
        (seuil - 1, M.REJET, M.FRAGILITE),
        (None, M.AIME, M.SANS_NOTE),
    ]
    for moyenne, affinite, attendu in cas:
        m = M.Matiere("p", "Matière", affinite, moyenne=moyenne)
        assert m.lecture == attendu, f"{moyenne}/{affinite} → {m.lecture}"
    assert M.Matiere("p", "M", M.AIME, moyenne=seuil).lecture == M.APPUI, \
        "la note au seuil compte comme réussie"


def t_moyenne_hors_bornes_refusee():
    import matieres as M
    for mauvaise in (-1, 21):
        try:
            M.Matiere("p", "M", M.AIME, moyenne=mauvaise).valider()
        except ValueError:
            continue
        raise AssertionError(f"moyenne {mauvaise} acceptée")


def t_matieres_liees_a_la_personne():
    import matieres as M
    pid = P.creer(P.Personne("Rose", "Ugo", "lycee", "lycee",
                             consentement_parental_date="2026-09-01"), BASE).id
    M.remplacer_tout(pid, [M.Matiere(pid, "SVT", M.AIME, moyenne=14.0),
                           M.Matiere(pid, "Anglais", M.REJET, moyenne=7.0)], BASE)
    assert len(M.lister(pid, BASE)) == 2
    assert M.moyenne_generale(pid, BASE) == 10.5
    M.remplacer_tout(pid, [M.Matiere(pid, "SVT", M.AIME, moyenne=14.0)], BASE)
    assert len(M.lister(pid, BASE)) == 1, "la liste doit être remplacée d'un bloc"
    P.supprimer(pid, BASE)
    assert M.lister(pid, BASE) == [], "les matières doivent suivre la fiche"


def t_bloc_scolaire_reprend_les_matieres_et_le_seuil():
    import matieres as M
    pid = P.creer(P.Personne("Bleu", "Zoé", "lycee", "lycee",
                             consentement_parental_date="2026-09-01"), BASE).id
    sid = S.creer(S.Seance(pid), BASE).id
    M.remplacer_tout(pid, [M.Matiere(pid, "SVT", M.AIME, moyenne=15.0)], BASE)
    texte = R.composer_scolaire(P.lire(pid, BASE), BASE)
    assert f"{M.SEUIL_REUSSITE:g}/20" in texte, "le seuil doit être rappelé"
    assert "SVT | 15/20 | aime | " + M.APPUI in texte
    rap = R.preparer(sid, BASE)
    assert "SVT" in rap.bloc_scolaire


def t_bloc_scolaire_vide_sans_matiere():
    pid = P.creer(P.Personne("Gris", "Tom", "college", "college",
                             consentement_parental_date="2026-09-01"), BASE).id
    assert R.composer_scolaire(P.lire(pid, BASE), BASE) == ""


def t_parcoursup_pour_les_lyceens_seulement():
    for public, attendu in (("lycee", True), ("college", False),
                            ("reconversion", False)):
        pid = P.creer(P.Personne("Noir", public.capitalize(), 
                                 "lycee" if public == "lycee" else
                                 "college" if public == "college" else "adulte",
                                 public,
                                 consentement_parental_date="2026-09-01"), BASE).id
        sid = S.creer(S.Seance(pid), BASE).id
        texte = R.composer_plan_action(P.lire(pid, BASE), sid, BASE)
        present = "Parcoursup" in texte
        assert present is attendu, f"{public} : Parcoursup {present}"


def t_aucune_date_parcoursup_en_dur():
    """Les dates changent à chaque campagne : seuls les mois sont écrits."""
    import re
    for echeance, action, moyens in R.ETAPES_PARCOURSUP:
        assert not re.search(r"\b\d{1,2}\s", echeance), f"date en dur : {echeance}"
        assert not re.search(r"\b20\d\d\b", echeance + action), f"année : {echeance}"
    texte = " ".join(e for e, a, m in R.ETAPES_PARCOURSUP)
    assert "janvier" in texte and "juin" in texte


# ── Module 4 ───────────────────────────────────────────────────────────────
def t_la_trame_a_huit_blocs():
    assert R.BLOCS == ("bloc_situation", "bloc_tests_utilises", "bloc_scolaire",
                       "bloc_resultats", "bloc_pistes", "bloc_competences",
                       "bloc_solutions", "bloc_references")
    for pub in P.PUBLICS:
        assert set(R.intitules(pub)) == set(R.BLOCS), f"intitulés incomplets : {pub}"


def t_le_bloc_scolaire_ne_concerne_que_les_scolaires():
    for pub in ("college", "lycee"):
        assert "bloc_scolaire" in R.blocs_pour(pub), pub
        assert len(R.blocs_pour(pub)) == 8
    for pub in ("reconversion", "vae", "handicap", "burnout"):
        assert "bloc_scolaire" not in R.blocs_pour(pub), pub
        assert len(R.blocs_pour(pub)) == 7


def t_trois_blocs_sont_des_tableaux():
    assert set(R.BLOCS_TABLEAU) == {"bloc_scolaire", "bloc_competences",
                                    "bloc_solutions"}
    assert len(R.BLOCS_TABLEAU["bloc_scolaire"]) == 4
    assert len(R.BLOCS_TABLEAU["bloc_competences"]) == 3
    assert len(R.BLOCS_TABLEAU["bloc_solutions"]) == 3


def t_les_blocs_du_public_sont_assembles_seuls():
    RT.creer(RT.ResultatTest(SID, "assessfirst_externe",
                             synthese_texte="Profil coordinateur"), BASE)
    rap = R.preparer(SID, BASE)
    pers = P.lire(PID, BASE)
    restants = [b for b in rap.blocs_vides if b in R.blocs_pour(pers.public)]
    assert restants == [], f"blocs encore vides : {restants}"
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


def t_plan_action_reprend_les_demarches_des_outils():
    import questionnaire as Q
    RT.creer(RT.ResultatTest(SID, "points_forts", reponses={"coches": ["f01"]},
                             synthese_texte="Points forts — 1 retenu"), BASE)
    pers = P.lire(PID, BASE)
    texte = R.composer_plan_action(pers, SID, BASE)
    suite = Q.disponibles()["points_forts"].get("suite", [])[0]
    assert suite in texte, "les démarches prévues par l'outil manquent"
    for ligne in texte.splitlines():
        assert ligne.count("|") == 2, f"ligne mal formée : {ligne!r}"
    assert texte.splitlines()[0].split("|")[0].strip() == "", \
        "l'échéance ne doit pas être décidée par l'outil"


def t_plan_action_ne_prescrit_pas_les_ressources():
    """Prescrire « prendre connaissance de X » à tout le monde serait
    inventer une démarche."""
    import ressources as Rs
    pers = P.lire(PID, BASE)
    texte = R.composer_plan_action(pers, SID, BASE)
    for r in Rs.pour_public(pers.public):
        assert r.url not in texte, f"{r.nom} prescrit dans le plan d'action"


def t_competences_viennent_des_cases_cochees():
    import questionnaire as Q
    pid = P.creer(P.Personne("Vert", "Luc", "adulte", "reconversion"), BASE).id
    sid = S.creer(S.Seance(pid), BASE).id
    q = Q.disponibles()["points_forts"]
    coche = q.items[0]["id"]
    RT.creer(RT.ResultatTest(sid, "points_forts", reponses={"coches": [coche]},
                             synthese_texte="un point fort"), BASE)
    qv = Q.disponibles()["points_vigilance"]
    RT.creer(RT.ResultatTest(sid, "points_vigilance",
                             reponses={"coches": [qv.items[0]["id"]]},
                             synthese_texte="un point de vigilance"), BASE)
    texte = R.composer_competences(sid, BASE)
    assert f"Savoir-être | {q.items[0]['texte']} | acquis" in texte
    assert f"Savoir-être | {qv.items[0]['texte']} | à développer" in texte
    assert "Savoirs |" in texte and "Savoir-faire |" in texte


def t_references_citent_les_sources_des_outils():
    import questionnaire as Q
    import ressources as Rs
    pers = P.lire(PID, BASE)
    texte = R.composer_references(pers, SID, BASE)
    assert Q.disponibles()["points_forts"].source in texte, "source non citée"
    for r in Rs.pour_public(pers.public):
        assert r.url in texte, f"{r.nom} absent des références"
        assert r.acces in texte


def t_pistes_restent_a_remplir():
    """La trame est là, le contenu non : c'est au consultant de nommer."""
    texte = R.composer_pistes(P.lire(PID, BASE))
    assert "Pistes explorées" in texte and "écartées" in texte
    assert "retenue" in texte.lower()
    assert texte.count("- ") == 3, "les lignes doivent rester vides"


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
    assert attendu in rap.bloc_references, "l'orientation de la personne manque"


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
