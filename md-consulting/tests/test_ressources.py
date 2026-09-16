"""Tests du catalogue de ressources. `python3 tests/test_ressources.py`"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import personne as P
import ressources as R

INTERDITS = ("centraltest", "bf5", "vocation", "profil pro", "e-stress")


def t_publics_connus():
    for r in R.RESSOURCES:
        assert r.publics, f"{r.nom} n'est rattachée à aucun public"
        inconnus = set(r.publics) - set(P.PUBLICS)
        assert not inconnus, f"{r.nom} : public(s) inconnu(s) {inconnus}"


def t_urls_https():
    for r in R.RESSOURCES:
        assert r.url.startswith("https://"), f"{r.nom} : URL non https"


def t_acces_renseigne():
    valides = {R.LIBRE, R.COMPTE_REQUIS, R.FREEMIUM, R.SERVICE_PUBLIC}
    for r in R.RESSOURCES:
        assert r.acces in valides, f"{r.nom} : statut d'accès invalide {r.acces!r}"


def t_aucun_produit_sous_licence_payante():
    """Garde-fou : le brief exclut explicitement les tests CentralTest."""
    for r in R.RESSOURCES:
        blob = f"{r.nom} {r.url} {r.description}".lower()
        for mot in INTERDITS:
            assert mot not in blob, f"{r.nom} : produit exclu détecté ({mot})"


def t_ressources_verifiees_pour_le_burn_out():
    """Ce public doit avoir la voie de soin, pas seulement des outils génériques."""
    noms = " ".join(r.nom for r in R.pour_public("burnout"))
    assert "INRS" in noms, "la référence officielle manque"
    assert "Mon soutien psy" in noms, "la voie de soin manque"


def t_mise_en_garde_burn_out():
    """Un écran burn-out doit dire que l'outil ne dépiste pas."""
    garde = R.MISES_EN_GARDE.get("burnout", "")
    assert garde, "aucune mise en garde pour ce public"
    for attendu in ("ne dépiste pas", "médecin du travail", "aucun score"):
        assert attendu in garde.lower() or attendu in garde, f"manque : {attendu}"


def t_aucun_instrument_de_burn_out_dans_les_questionnaires():
    """Un score d'épuisement est une donnée de santé : il n'entre pas ici."""
    import questionnaire as Q
    interdits = ("burnout", "burn-out", "maslach", "mbi", "epuisement",
                 "épuisement", "copenhagen")
    for cle, q in Q.disponibles().items():
        blob = (cle + " " + q.titre + " " + str(q.get("source", ""))).lower()
        for mot in interdits:
            assert mot not in blob, f"{cle} : instrument d'épuisement détecté ({mot})"


def t_freemium_porte_un_avertissement():
    """Un outil non entièrement gratuit ne peut pas être listé sans mention."""
    for r in R.RESSOURCES:
        if r.acces in (R.FREEMIUM, R.COMPTE_REQUIS):
            assert r.note.strip(), f"{r.nom} : accès {r.acces} sans note explicative"


def t_cvdesignr_present_et_qualifie():
    cv = [r for r in R.RESSOURCES if "cvdesignr" in r.url]
    assert len(cv) == 1, "CVDesignR absent ou en double"
    assert cv[0].acces == R.FREEMIUM, "CVDesignR n'est pas entièrement gratuit"


def t_chaque_public_a_au_moins_une_ressource():
    vides = [k for k in P.PUBLICS if not R.pour_public(k)]
    assert not vides, f"public(s) sans aucune ressource : {vides}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    echecs = 0
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except Exception as exc:
            echecs += 1
            print(f"  ÉCHEC {t.__name__} : {exc}")
    print(f"\n{len(tests) - echecs}/{len(tests)} tests passés")
    sys.exit(1 if echecs else 0)
