"""Découpage des réponses longues pour Telegram."""

from __future__ import annotations

from app.bot.telegram import decouper_message

LIMITE = 4096


def test_message_court_non_decoupe():
    assert decouper_message("Bonjour") == ["Bonjour"]


def test_message_vide():
    assert decouper_message("") == []
    assert decouper_message("   ") == []


def test_respecte_la_limite_telegram():
    texte = "phrase de test. " * 2000
    morceaux = decouper_message(texte, LIMITE)
    assert len(morceaux) > 1
    assert all(len(m) <= LIMITE for m in morceaux)


def test_ne_coupe_pas_au_milieu_dun_mot():
    texte = "anticonstitutionnellement " * 500
    for morceau in decouper_message(texte, 1000):
        assert not morceau.endswith("antic")
        assert " " in morceau


def test_prefere_les_frontieres_de_paragraphe():
    texte = "\n\n".join(f"Paragraphe numéro {i}. " * 20 for i in range(20))
    morceaux = decouper_message(texte, 2000)
    assert len(morceaux) > 1
    # Aucun morceau ne doit commencer par une fin de phrase orpheline.
    assert all(not m.startswith(". ") for m in morceaux)


def test_blocs_de_code_refermes():
    """Un bloc de code coupé casserait le rendu de toute la conversation."""
    texte = "Voici le code :\n\n```\n" + ("ligne de code\n" * 800) + "```\n\nFin."
    morceaux = decouper_message(texte, LIMITE)
    assert len(morceaux) > 1
    for morceau in morceaux:
        assert morceau.count("```") % 2 == 0, "bloc de code non refermé"


def test_contenu_integralement_preserve():
    """Aucun mot ne doit disparaître au découpage."""
    texte = " ".join(f"mot{i}" for i in range(3000))
    morceaux = decouper_message(texte, LIMITE)
    reconstruit = " ".join(morceaux).split()
    assert reconstruit == texte.split()


def test_limite_personnalisee():
    morceaux = decouper_message("a " * 5000, 512)
    assert all(len(m) <= 512 for m in morceaux)
