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
