"""Pipeline RAG : recherche, sélection, contexte, citations."""

from __future__ import annotations

import pytest

from app.ai.context_builder import Source, construire, formater_sources, selectionner
from app.ai.rag import MoteurRAG, citations_utilisees
from app.config import Settings, get_settings
from tests.conftest import FausseRecherche, FauxProvider, resultat


def _settings(**extra) -> Settings:
    get_settings.cache_clear()
    return Settings(TELEGRAM_BOT_TOKEN="t", ANTHROPIC_API_KEY="k", **extra)


async def test_recuperation_construit_un_contexte():
    s = _settings(RAG_CANDIDATES=30, RAG_FINAL_CHUNKS=3, RAG_MIN_SCORE=0.0)
    recherche = FausseRecherche(
        [resultat(chunk_id=f"c{i}", document_id=f"d{i}", score=0.9 - i / 100, text=f"passage {i}")
         for i in range(10)]
    )
    moteur = MoteurRAG(s, FauxProvider(), recherche)
    contexte = await moteur.recuperer("Que dit le règlement ?")

    assert contexte.a_des_sources
    assert contexte.retenus == 3
    assert contexte.candidats == 10
    assert "<documents>" in contexte.contexte
    assert "[1]" in contexte.contexte


async def test_le_nombre_de_candidats_depasse_le_contexte_final():
    """Chercher large, envoyer étroit : les deux réglages sont distincts."""
    s = _settings(RAG_CANDIDATES=25, RAG_FINAL_CHUNKS=4, RAG_MIN_SCORE=0.0)
    recherche = FausseRecherche(
        [resultat(chunk_id=f"c{i}", document_id=f"d{i}", score=0.8, text=f"texte varié {i}") for i in range(25)]
    )
    moteur = MoteurRAG(s, FauxProvider(), recherche)
    contexte = await moteur.recuperer("question")

    assert recherche.derniere_limite == 25
    assert contexte.retenus == 4


async def test_aucun_resultat_donne_un_contexte_vide_mais_valide():
    """Sans document, Joshua doit pouvoir répondre « je ne sais pas »."""
    s = _settings()
    moteur = MoteurRAG(s, FauxProvider(), FausseRecherche([]))
    contexte = await moteur.recuperer("question sans réponse")

    assert contexte.a_des_sources is False
    assert "aucun extrait pertinent" in contexte.contexte


async def test_question_vide():
    s = _settings()
    moteur = MoteurRAG(s, FauxProvider(), FausseRecherche([resultat()]))
    contexte = await moteur.recuperer("   ")
    assert contexte.a_des_sources is False


async def test_seuil_de_score_ecarte_le_bruit():
    s = _settings(RAG_MIN_SCORE=0.5, RAG_FINAL_CHUNKS=5)
    recherche = FausseRecherche(
        [resultat(chunk_id="bon", score=0.8, text="pertinent"),
         resultat(chunk_id="bruit", document_id="d2", score=0.2, text="hors sujet")]
    )
    moteur = MoteurRAG(s, FauxProvider(), recherche)
    contexte = await moteur.recuperer("question")
    assert contexte.retenus == 1


async def test_cache_embedding_evite_un_second_encodage():
    class FauxRedis:
        def __init__(self):
            self.donnees = {}

        async def get(self, cle):
            return self.donnees.get(cle)

        async def setex(self, cle, ttl, valeur):
            self.donnees[cle] = valeur

    s = _settings(RAG_MIN_SCORE=0.0)
    provider = FauxProvider()
    moteur = MoteurRAG(s, provider, FausseRecherche([resultat()]), redis_client=FauxRedis())

    await moteur.recuperer("même question")
    appels_apres_premier = provider.appels
    await moteur.recuperer("même question")
    assert provider.appels == appels_apres_premier, "la seconde requête aurait dû être servie par le cache"


def test_diversification_evite_les_doublons():
    """Sans MMR, les meilleurs résultats sont dix fois le même passage."""
    candidats = [resultat(chunk_id=f"c{i}", document_id="d1", score=0.95 - i / 1000,
                          text="exactement le même passage répété ici") for i in range(5)]
    candidats.append(resultat(chunk_id="autre", document_id="d2", score=0.6,
                              text="un contenu totalement différent apportant autre chose"))
    retenus = selectionner(candidats, limite=3, lambda_mmr=0.5)
    assert any(r.chunk_id == "autre" for r in retenus)


def test_plafond_par_document():
    """Un ouvrage volumineux ne doit pas monopoliser le contexte."""
    candidats = [resultat(chunk_id=f"c{i}", document_id="dominant", score=0.9,
                          text=f"contenu distinct numéro {i}") for i in range(10)]
    candidats += [resultat(chunk_id=f"x{i}", document_id=f"autre{i}", score=0.5,
                           text=f"autre source {i}") for i in range(5)]
    retenus = selectionner(candidats, limite=8, max_par_document=4)
    assert sum(1 for r in retenus if r.document_id == "dominant") <= 4


def test_contexte_borne_en_caracteres():
    candidats = [resultat(chunk_id=f"c{i}", document_id=f"d{i}", text="x" * 1000) for i in range(20)]
    extraits, sources = construire(candidats, max_chars=3000)
    assert sum(len(e) for e in extraits) <= 3000 + 1100  # un extrait entier de marge
    assert len(sources) == len(extraits)


def test_les_references_viennent_des_metadonnees():
    """Une citation ne peut contenir que ce que Qdrant a réellement renvoyé."""
    extraits, sources = construire([resultat(filename="Manuel_X.pdf", page=47)], max_chars=10_000)
    assert sources[0].libelle() == "Manuel_X.pdf — page 47"
    assert "Manuel_X.pdf — page 47" in extraits[0]


def test_reference_sans_page_utilise_la_section():
    extraits, sources = construire(
        [resultat(filename="Reglement.pdf", page=None, section="3.2")], max_chars=10_000
    )
    assert sources[0].libelle() == "Reglement.pdf — 3.2"


def test_citations_reellement_utilisees():
    sources = [Source(1, "a.pdf", 1, None, "d", "c", 0.9), Source(2, "b.pdf", 2, None, "d", "c", 0.8)]
    assert citations_utilisees("Réponse appuyée sur [1].", sources) == {1}
    assert formater_sources(sources, {1}) == "[1] a.pdf — page 1"


def test_citation_fantome_ecartee():
    """Un numéro inventé par le modèle ne doit jamais être présenté."""
    sources = [Source(1, "a.pdf", 1, None, "d", "c", 0.9)]
    assert citations_utilisees("Voir [1] et [9].", sources) == {1}
    assert "9" not in formater_sources(sources, citations_utilisees("Voir [1] et [9].", sources))
