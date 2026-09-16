"""Vérifie la transcription des outils d'investigation MD Consulting.
`python3 tests/test_questionnaires.py`

Ces tests ne jugent pas le contenu : ils vérifient qu'il est complet et
cohérent avec les grilles du document source. Une transcription tronquée
ou une clé de cotation incomplète les fait échouer.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import questionnaire as Q
import resultat_test as RT

INSTALLES = Q.disponibles()

# Effectifs relevés sur le document source. Un écart = transcription abîmée.
ATTENDUS = {
    "projet_de_vie": ("choix_groupes", 25),
    "freins": ("checklist", 26),
    "motivations_35": ("selection_n", 35),
    "valeurs": ("checklist", 48),
    "points_forts": ("checklist", 64),
    "points_vigilance": ("checklist", 33),
    "bilan_360": ("matrice_360", 68),
    "bilan_360_scolaire": ("matrice_360", 68),
    "enquete_metier": ("questions_ouvertes", 11),
    "predisposition_creation_entreprise": ("likert", 20),
    "orientation_formateur": ("ab", 30),
}


def t_tous_les_outils_sont_installes():
    manquants = set(ATTENDUS) - set(INSTALLES)
    assert not manquants, f"outils absents : {sorted(manquants)}"


def t_effectifs_conformes_au_document():
    for cle, (forme, nb) in ATTENDUS.items():
        q = INSTALLES[cle]
        assert q.forme == forme, f"{cle} : forme {q.forme} au lieu de {forme}"
        assert q.nb_items == nb, f"{cle} : {q.nb_items} items au lieu de {nb}"


def t_chaque_outil_cite_sa_source():
    for cle, q in INSTALLES.items():
        assert q.get("source"), f"{cle} : aucune source citée"


def t_grille_des_motivations_couvre_les_35_items():
    q = INSTALLES["motivations_35"]
    couverts = sorted(int(i) for p in q.profils.values() for i in p["items"])
    assert couverts == list(range(1, 36)), "la grille ne couvre pas 1 à 35 une seule fois"
    assert len(q.profils) == 5
    for nom, p in q.profils.items():
        assert len(p["items"]) == 7, f"{nom} : {len(p['items'])} items au lieu de 7"
        assert p["description"].strip(), f"{nom} : description absente"


def t_profil_dominant_calcule():
    q = INSTALLES["motivations_35"]
    # sept items du Profil 5, trois du Profil 1
    choisis = q.profils["Profil 5"]["items"] + q.profils["Profil 1"]["items"][:3]
    comptes = Q.profils_par_selection(q, choisis)
    assert comptes[0] == ("Profil 5", 7), comptes


def t_cle_du_test_formateur_couvre_les_30_items():
    q = INSTALLES["orientation_formateur"]
    cotes = sorted(int(i) for axe in q.axes for i in axe["cle"])
    assert cotes == list(range(1, 31)), "clé de cotation incomplète"
    assert len(q.axes) == 2
    for axe in q.axes:
        assert len(axe["cle"]) == 15, f"{axe['nom']} : {len(axe['cle'])} items"
        assert set(axe["cle"].values()) <= {"A", "B"}
    assert len(q.familles) == 5


def t_score_du_test_creation_entreprise():
    q = INSTALLES["predisposition_creation_entreprise"]
    reponses = {str(i): "Tout à fait vrai" for i in range(1, 21)}
    assert Q.score_likert(q, reponses)["total"] == 80
    reponses = {str(i): "Pas du tout vrai" for i in range(1, 21)}
    score = Q.score_likert(q, reponses)
    assert score["total"] == 20 and "prématuré" in score["lecture"]


def t_thematiques_non_devinees():
    """Le document source ne rattache pas les items aux 6 thématiques.
    Elles doivent rester vides plutôt qu'être remplies au jugé."""
    q = INSTALLES["predisposition_creation_entreprise"]
    assert len(q.thematiques) == 6
    assert all(t["items"] == [] for t in q.thematiques)
    reponses = {str(i): "Plutôt vrai" for i in range(1, 21)}
    assert Q.score_likert(q, reponses)["thematiques"] == {}
    assert "INCOMPLET" in q.get("note", ""), "l'absence doit être signalée"


def t_les_deux_versions_du_360_partagent_les_items():
    a, b = INSTALLES["bilan_360"], INSTALLES["bilan_360_scolaire"]
    ids_a = [i["id"] for g in a.groupes for i in g["items"]]
    ids_b = [i["id"] for g in b.groupes for i in g["items"]]
    assert ids_a == ids_b
    assert len(a.evaluateurs) == 6 and len(b.evaluateurs) == 7
    assert "Parents" in b.evaluateurs and "Parents" not in a.evaluateurs


def t_valeurs_portent_leurs_definitions():
    q = INSTALLES["valeurs"]
    definies = [i for i in q.items if i.get("definition")]
    assert len(definies) >= 45, f"seulement {len(definies)} valeurs définies"


def t_projet_de_vie_va_de_a_a_y():
    q = INSTALLES["projet_de_vie"]
    ids = [x["id"] for s in q.sections for x in s["questions"]]
    assert ids == [chr(c) for c in range(ord("a"), ord("y") + 1)], ids
    assert len(q.sections) == 10
    for s in q.sections:
        for question in s["questions"]:
            assert len(question["choix"]) >= 2, f"{question['id']} : trop peu de choix"


# ── Ciblage par public ─────────────────────────────────────────────────────
def t_chaque_outil_declare_ses_publics():
    import personne as P
    for cle, q in INSTALLES.items():
        cibles = q.get("publics")
        assert cibles, f"{cle} : aucun public déclaré"
        inconnus = set(cibles) - set(P.PUBLICS)
        assert not inconnus, f"{cle} : public(s) inconnu(s) {sorted(inconnus)}"
        assert q.get("note_publics"), f"{cle} : ciblage non justifié"


def t_chaque_public_a_au_moins_un_outil():
    import personne as P
    vides = [k for k in P.PUBLICS if not Q.pour_public(k)]
    assert not vides, f"public(s) sans aucun outil : {vides}"


def t_le_360_scolaire_va_aux_scolaires_et_l_autre_aux_adultes():
    assert set(INSTALLES["bilan_360_scolaire"].publics) == {"college", "lycee"}
    adultes = set(INSTALLES["bilan_360"].publics)
    assert "college" not in adultes and "lycee" not in adultes


def t_outils_de_vie_salariee_hors_college():
    """Un collégien n'a pas à passer un outil qui parle de CDI ou de chômage."""
    for cle in ("motivations_35", "freins", "projet_de_vie",
                "predisposition_creation_entreprise", "orientation_formateur"):
        assert "college" not in INSTALLES[cle].publics, f"{cle} proposé au collège"


def t_creation_entreprise_hors_mineurs_et_burnout():
    cibles = set(INSTALLES["predisposition_creation_entreprise"].publics)
    assert cibles == {"reconversion", "vae"}, cibles


def t_item_intime_ecarte_pour_un_mineur():
    """« intimité sexuelle » n'a pas à être soumis à un collégien."""
    q = INSTALLES["valeurs"]
    adulte = {i["id"] for i in Q.items_pour(q, est_mineur=False)}
    mineur = {i["id"] for i in Q.items_pour(q, est_mineur=True)}
    assert adulte - mineur == {"v05"}, adulte - mineur
    ecarte = Q.items_ecartes(q, est_mineur=True)
    assert len(ecarte) == 1 and "sexuel" in ecarte[0]["definition"]
    assert Q.items_ecartes(q, est_mineur=False) == []


def t_donnee_sensible_signalee():
    """La conviction religieuse relève de l'article 9 du RGPD."""
    q = INSTALLES["valeurs"]
    sensibles = [i for i in q.items if i.get("sensible")]
    assert sensibles, "aucun item sensible signalé"
    assert any("article 9" in i["sensible"] for i in sensibles)


def t_public_inconnu_refuse_au_chargement():
    import json, tempfile
    d = Path(tempfile.mkdtemp())
    (d / "ko.json").write_text(json.dumps({
        "cle": "k", "titre": "K", "forme": "checklist", "publics": ["martiens"],
        "items": [{"id": "a", "texte": "A"}]}, ensure_ascii=False), encoding="utf-8")
    try:
        Q.disponibles(d)
    except Q.QuestionnaireInvalide as exc:
        assert "martiens" in str(exc)
        return
    raise AssertionError("public inconnu accepté")


def t_les_types_de_test_suivent_les_fichiers():
    """Ajouter un questionnaire doit suffire à le rendre enregistrable."""
    types = RT.types()
    for cle in ATTENDUS:
        assert cle in types, f"{cle} non enregistrable"
    for cle in RT.TYPES_EXTERNES:
        assert cle in types


def t_outil_inconnu_refuse():
    r = RT.ResultatTest("seance", "outil_qui_nexiste_pas")
    try:
        r.valider()
    except ValueError:
        return
    raise AssertionError("type de test inconnu accepté")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    echecs = 0
    for t in tests:
        try:
            t(); print(f"  OK   {t.__name__}")
        except Exception as exc:
            echecs += 1; print(f"  ÉCHEC {t.__name__} : {type(exc).__name__} {exc}")
    print(f"\n{len(tests) - echecs}/{len(tests)} tests passés")
    sys.exit(1 if echecs else 0)
