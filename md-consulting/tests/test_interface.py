"""Test de l'interface réelle via st.testing.AppTest.
Exécute le script Streamlit sans navigateur. `python3 tests/test_interface.py`
"""
import sys, tempfile, os
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# La base de test doit être choisie AVANT que app.py n'appelle db.initialiser()
import db
db.CHEMIN_BASE = Path(tempfile.mktemp(suffix=".db"))
db.initialiser(db.CHEMIN_BASE)

from streamlit.testing.v1 import AppTest
import personne as P, seance as S

APP = str(RACINE / "app.py")


def _lancer(**etat):
    at = AppTest.from_file(APP, default_timeout=30)
    for cle, valeur in etat.items():
        at.session_state[cle] = valeur
    return at.run()


def t_ecran_liste_sans_exception():
    at = _lancer()
    assert not at.exception, at.exception
    assert any("fiche" in m.value for m in at.subheader)


def t_formulaire_creation_sans_exception():
    at = _lancer(page_personne="creation")
    assert not at.exception, at.exception
    assert at.text_input, "aucun champ de saisie affiché"


def t_interface_bloque_un_mineur_sans_consentement():
    at = _lancer(page_personne="creation")
    at.text_input[0].set_value("Martin")          # nom
    at.text_input[1].set_value("Léa")             # prénom
    at.selectbox[0].set_value("college")          # tranche d'âge
    at.selectbox[1].set_value("college")          # public
    at = at.run()
    enregistrer = [b for b in at.button if b.label == "Enregistrer"]
    assert enregistrer, "bouton « Enregistrer » introuvable"
    enregistrer[0].click()
    at = at.run()
    assert not at.exception, at.exception
    assert at.error, "aucune erreur affichée pour un mineur sans consentement"
    assert "bloqué" in at.error[0].value.lower(), at.error[0].value
    ecrites = [x.nom for x in P.lister(chemin=db.CHEMIN_BASE)]
    assert "Martin" not in ecrites, "la fiche du mineur a été écrite malgré le blocage"


def t_ecran_fiche_et_seance():
    pid = P.creer(P.Personne("Dupont", "Jean", "adulte", "reconversion"), db.CHEMIN_BASE).id
    at = _lancer(personne_id=pid)
    assert not at.exception, at.exception
    sid = S.creer(S.Seance(pid), db.CHEMIN_BASE).id
    at = _lancer(seance_id=sid)
    assert not at.exception, at.exception
    textes = " ".join(m.value for m in at.subheader)
    assert "Séance" in textes and "Compte rendu" in textes, textes


def t_chaque_questionnaire_s_affiche_sans_exception():
    """Onze formulaires, sept formes d'affichage : chacun doit se rendre.
    Chaque outil est ouvert avec une personne du public qu'il vise — sinon le
    filtrage l'écarterait et le test ne prouverait rien."""
    import questionnaire as Q
    from datetime import date, timedelta
    seances = {}
    for public in P.PUBLICS:
        naissance = None
        if public in ("college", "lycee"):
            age = 13 if public == "college" else 16
            naissance = (date.today() - timedelta(days=age * 366)).isoformat()
        pers = P.creer(P.Personne("Passation", public.capitalize(),
                                  "college" if public == "college"
                                  else "lycee" if public == "lycee" else "adulte",
                                  public, date_naissance=naissance,
                                  consentement_parental_date=date.today().isoformat()
                                  if naissance else None), db.CHEMIN_BASE)
        seances[public] = S.creer(S.Seance(pers.id), db.CHEMIN_BASE).id

    echecs, ouverts = [], 0
    for cle, q in Q.disponibles().items():
        public = q.publics[0]
        at = _lancer(seance_id=seances[public], questionnaire_en_cours=cle)
        if at.exception:
            echecs.append(f"{cle} ({public}) : {at.exception}")
            continue
        titres = " ".join(m.value for m in at.subheader)
        if q.titre not in titres:
            echecs.append(f"{cle} ({public}) : le titre ne s'affiche pas — {titres}")
        else:
            ouverts += 1
    assert not echecs, "\n".join(echecs)
    assert ouverts == 11, f"{ouverts} questionnaires ouverts sur 11"


def t_item_intime_non_soumis_a_un_college_dans_l_interface():
    """Vérifié à l'écran, pas seulement dans le modèle."""
    from datetime import date, timedelta
    import questionnaire as Q
    naissance = (date.today() - timedelta(days=13 * 366)).isoformat()
    pers = P.creer(P.Personne("Tissot", "Rémi", "college", "college",
                              date_naissance=naissance,
                              consentement_parental_date=date.today().isoformat()),
                   db.CHEMIN_BASE)
    sid = S.creer(S.Seance(pers.id), db.CHEMIN_BASE).id
    at = _lancer(seance_id=sid, questionnaire_en_cours="valeurs")
    assert not at.exception, at.exception
    libelles = [c.label for c in at.checkbox]
    assert not any(l.startswith("Amour") for l in libelles), \
        "l'item « Amour — intimité sexuelle » est proposé à un collégien"
    assert any(l.startswith("Ambition") for l in libelles), \
        "les autres valeurs devraient rester proposées"
    assert any("mineure" in m.value for m in at.info), \
        "l'écran devrait dire ce qui a été écarté"


def t_mise_en_garde_burn_out_visible_a_l_ecran():
    """La personne en épuisement : l'écran doit dire que l'outil ne dépiste pas."""
    pers = P.creer(P.Personne("Blanc", "Eve", "adulte", "burnout"), db.CHEMIN_BASE)
    sid = S.creer(S.Seance(pers.id), db.CHEMIN_BASE).id
    at = _lancer(seance_id=sid)
    assert not at.exception, at.exception
    avertissements = " ".join(m.value for m in at.warning)
    assert "ne dépiste pas le burn-out" in avertissements, avertissements
    assert "médecin du travail" in avertissements


def t_ecran_ressources_sans_exception():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value("Ressources")
    at = at.run()
    assert not at.exception, at.exception
    assert any("Ressources" in m.value for m in at.subheader)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    echecs = 0
    for t in tests:
        try:
            t(); print(f"  OK   {t.__name__}")
        except Exception as exc:
            echecs += 1; print(f"  ÉCHEC {t.__name__} : {type(exc).__name__} {exc}")
    os.path.exists(db.CHEMIN_BASE) and os.remove(db.CHEMIN_BASE)
    print(f"\n{len(tests) - echecs}/{len(tests)} tests passés")
    sys.exit(1 if echecs else 0)
