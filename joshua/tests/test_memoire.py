"""Mémoire conversationnelle : format attendu par l'API Anthropic."""

from __future__ import annotations

from dataclasses import dataclass

from app.memory.conversation import construire_historique


@dataclass
class FauxMessage:
    role: str
    content: str


def test_historique_vide():
    assert construire_historique([], None) == []


def test_roles_alternes():
    """L'API refuse deux messages du même rôle à la suite."""
    messages = [FauxMessage("user", "A"), FauxMessage("user", "B"), FauxMessage("assistant", "C")]
    historique = construire_historique(messages, None)
    roles = [m["role"] for m in historique]
    assert roles == ["user", "assistant"]
    assert historique[0]["content"] == "A\n\nB"


def test_commence_toujours_par_user():
    historique = construire_historique([FauxMessage("assistant", "Bonjour"), FauxMessage("user", "Salut")], None)
    assert historique[0]["role"] == "user"


def test_resume_injecte_comme_premier_tour():
    """Le résumé n'entre pas dans le prompt système : celui-ci décrit le
    comportement de Joshua, pas l'état d'une conversation."""
    historique = construire_historique([FauxMessage("user", "Question")], "Résumé du passé")
    assert historique[0]["role"] == "user"
    assert "Résumé du passé" in historique[0]["content"]
    assert historique[1]["role"] == "assistant"
    assert historique[-1]["content"] == "Question"


def test_messages_vides_ignores():
    historique = construire_historique(
        [FauxMessage("user", "  "), FauxMessage("user", "vraie question")], None
    )
    assert len(historique) == 1
    assert historique[0]["content"] == "vraie question"
