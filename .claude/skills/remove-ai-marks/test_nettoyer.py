"""Tests du nettoyeur de marques invisibles.

La propriété qui compte le plus n'est pas ce que l'outil retire, mais ce
qu'il laisse : un texte propre doit en ressortir IDENTIQUE, octet pour
octet. C'est ce qui permet de le passer sans crainte sur n'importe quel
fichier, y compris ceux qui contiennent de l'hébreu, du grec ou du
cyrillique légitimes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nettoyer import nettoyer  # noqa: E402


def _texte(s: str) -> str:
    return nettoyer(s)[0]


# ── Invisibles ──────────────────────────────────────────────────────
def test_espace_sans_chasse_retiree():
    assert _texte("jo​shua") == "joshua"


def test_marque_ordre_octets_retiree():
    assert _texte("﻿Première ligne") == "Première ligne"


def test_trait_dunion_conditionnel_retire():
    assert _texte("insé­cable") == "insécable"


def test_marques_directionnelles_retirees():
    assert _texte("Rite ‏Brith‎ Israël") == "Rite Brith Israël"


def test_liants_conserves_par_defaut():
    """ZWJ et ZWNJ sont invisibles mais SIGNIFIANTS en arabe, en hébreu
    et dans les écritures indiennes. Les retirer sans le dire
    corromprait le texte au lieu de le nettoyer."""
    assert _texte("א‍ב") == "א‍ב"


def test_liants_retires_sur_demande():
    assert nettoyer("א‍ב", sans_liants=True)[0] == "אב"


# ── Espaces ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("exotique", [" ", " ", " ", " ",
                                      " ", "　"])
def test_espaces_exotiques_normalisees(exotique):
    assert _texte(f"Rite{exotique}Brith") == "Rite Brith"


def test_recherche_redevient_possible():
    """Le symptôme réel : une recherche de « Rite Brith » échoue si une
    insécable s'est glissée entre les deux mots."""
    pollue = "Le Rite Brith Israël"
    assert "Rite Brith" not in pollue
    assert "Rite Brith" in _texte(pollue)


# ── Homoglyphes ─────────────────────────────────────────────────────
def test_homoglyphe_dans_un_mot_latin():
    """« Ореn » avec un O et un e cyrilliques se lit « Open » au pixel
    près, et ne se trouve jamais par une recherche."""
    assert _texte("Ореn") == "Open"


def test_texte_cyrillique_legitime_intact():
    """Une substitution globale détruirait tout texte réellement russe.
    Le contexte est la seule règle défendable."""
    russe = "Москва и Россия"
    assert _texte(russe) == russe


def test_texte_grec_legitime_intact():
    grec = "Λόγος καὶ Νόμος"
    assert _texte(grec) == grec


def test_mot_majoritairement_cyrillique_intact():
    """Un mot russe contenant une lettre latine reste un mot russe."""
    assert _texte("Москваo") == "Москваo"


# ── Innocuité ───────────────────────────────────────────────────────
def test_texte_propre_inchange():
    propre = ("Le Rite Brith Israël compte sept degrés correspondant aux sept "
              "Séphirot du plan inférieur : Malkuth, Yesod, Hod.")
    assert _texte(propre) == propre


def test_hebreu_intact():
    assert _texte("מוסיקה ואסטרונומיה") == "מוסיקה ואסטרונומיה"


def test_ponctuation_et_chiffres_intacts():
    assert _texte("12:30 — https://example.org/a?b=1") == "12:30 — https://example.org/a?b=1"


def test_normalisation_nfc():
    """« é » composé et « e + accent » se ressemblent et ne se comparent
    pas ; la forme composée est celle qu'attendent les moteurs."""
    decompose = "équerre"
    assert _texte(decompose) == "équerre"


def test_nfc_desactivable():
    decompose = "équerre"
    assert nettoyer(decompose, normaliser=False)[0] == decompose


# ── Rapport ─────────────────────────────────────────────────────────
def test_compte_par_famille():
    _, compte = nettoyer("a​b c​d")
    assert compte["espace sans chasse"] == 2
    assert compte["espace insécable"] == 1


def test_texte_propre_ne_signale_rien():
    assert nettoyer("Rite Brith Israël")[1] == {}


# ── Typographie française ───────────────────────────────────────────
def test_insecables_francaises_retablies():
    texte, _ = nettoyer("Voici : un test ; oui ! vraiment ?", francais=True)
    assert texte == "Voici : un test ; oui ! vraiment ?"


def test_guillemets_francais():
    texte, _ = nettoyer("Il dit «  bonjour  ».", francais=True)
    assert texte.startswith("Il dit « bonjour")


def test_heure_non_espacee():
    """Les deux-points d'un horaire ne prennent pas d'espace fine."""
    texte, _ = nettoyer("Rendez-vous à 12:30.", francais=True)
    assert "12:30" in texte


def test_typographie_francaise_non_appliquee_par_defaut():
    assert _texte("Voici : un test") == "Voici : un test"
