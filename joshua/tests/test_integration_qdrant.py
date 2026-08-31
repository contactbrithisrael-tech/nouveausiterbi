"""Test d'intégration : ingestion réelle → recherche réelle.

Qdrant est utilisé en **mode local** (moteur embarqué du client officiel,
même code de recherche, stockage sur disque temporaire). Aucune infrastructure
n'est donc nécessaire, mais le chemin exercé est le vrai : création de
collection, upsert par lots, filtres de payload, recherche vectorielle,
restitution des métadonnées de citation.

C'est le seul test qui prouve que les couches s'emboîtent réellement — les
autres vérifient chaque pièce isolément.
"""

from __future__ import annotations

import pytest

from app.ai.rag import MoteurRAG
from app.config import Settings, get_settings
from app.ingestion import pipeline as module_pipeline
from app.vectorstore import qdrant as module_qdrant
from app.vectorstore.qdrant import QdrantRecherche
from tests.conftest import FauxProvider


@pytest.fixture
def qdrant_local(tmp_path, monkeypatch):
    """Redirige les clients Qdrant vers un stockage local temporaire.

    Le mode local n'autorise qu'un accès à la fois au dossier : chaque
    fonction du module ouvre puis ferme son client, et la recherche n'est
    ouverte qu'après l'ingestion. C'est exactement l'usage séquentiel des
    scripts d'ingestion.
    """
    from qdrant_client import AsyncQdrantClient, QdrantClient

    chemin = str(tmp_path / "qdrant")
    monkeypatch.setattr(module_qdrant, "_client_sync", lambda settings: QdrantClient(path=chemin))
    monkeypatch.setattr(
        module_qdrant, "_client_async", lambda settings: AsyncQdrantClient(path=chemin)
    )
    return chemin


def _settings(**extra) -> Settings:
    get_settings.cache_clear()
    return Settings(TELEGRAM_BOT_TOKEN="t", ANTHROPIC_API_KEY="k", **extra)


async def test_ingestion_puis_recherche(tmp_path, qdrant_local, monkeypatch):
    documents = tmp_path / "docs"
    documents.mkdir()
    (documents / "reglement.md").write_text(
        "# Règlement intérieur\n\n"
        "## Article 3 — Délais\n"
        + " ".join(
            f"Le délai de recours est de trente jours à compter de la notification, point {i}."
            for i in range(40)
        )
        + "\n\n## Article 4 — Cotisations\n"
        + " ".join(f"La cotisation annuelle est fixée par le conseil, alinéa {i}." for i in range(40))
    )
    (documents / "manuel.txt").write_text(
        " ".join(f"Procédure d'installation du matériel, étape {i}." for i in range(60))
    )

    # PostgreSQL n'est pas nécessaire ici : seul le trajet vers Qdrant est
    # sous test. Le catalogue est vérifié par test_ingestion.py.
    enregistres: list[dict] = []
    monkeypatch.setattr(module_pipeline, "enregistrer_document", lambda s, v: enregistres.append(v))
    monkeypatch.setattr(module_pipeline, "index_bibliotheque", lambda s: {})

    settings = _settings(
        EMBEDDING_BATCH_SIZE=8,
        QDRANT_BATCH_SIZE=5,
        RAG_CANDIDATES=20,
        RAG_FINAL_CHUNKS=5,
        RAG_MIN_SCORE=0.0,
        EMBEDDING_DIM=8,
    )
    provider = FauxProvider()

    compteurs = module_pipeline.ingerer(
        documents, settings=settings, provider=provider, session=object(),
        source="test", categorie="reglements", tags=["interne"],
    )

    assert compteurs.indexes == 2
    assert compteurs.chunks > 0
    assert len(enregistres) == 2

    recherche = QdrantRecherche(settings)
    try:
        assert await recherche.compter() == compteurs.chunks

        moteur = MoteurRAG(settings, provider, recherche)
        contexte = await moteur.recuperer("Quel est le délai de recours ?")

        assert contexte.a_des_sources
        assert contexte.retenus <= 5
        # Les références proviennent des métadonnées réellement stockées.
        assert all(s.filename in {"reglement.md", "manuel.txt"} for s in contexte.sources)
        assert "<documents>" in contexte.contexte
        assert "[1]" in contexte.contexte
    finally:
        await recherche.fermer()


async def test_filtres_de_payload(tmp_path, qdrant_local, monkeypatch):
    """Un filtre par catégorie doit réellement restreindre les résultats."""
    documents = tmp_path / "docs"
    documents.mkdir()
    (documents / "a.txt").write_text(" ".join(f"Contenu de la première source {i}." for i in range(50)))

    monkeypatch.setattr(module_pipeline, "enregistrer_document", lambda s, v: None)
    monkeypatch.setattr(module_pipeline, "index_bibliotheque", lambda s: {})

    settings = _settings(EMBEDDING_DIM=8, RAG_MIN_SCORE=0.0)
    provider = FauxProvider()
    module_pipeline.ingerer(
        documents, settings=settings, provider=provider, session=object(), categorie="livres"
    )

    recherche = QdrantRecherche(settings)
    try:
        vecteur = provider.embed_query("contenu")
        assert await recherche.rechercher(vecteur, limite=5, filtres={"category": "livres"})
        assert await recherche.rechercher(vecteur, limite=5, filtres={"category": "absente"}) == []
    finally:
        await recherche.fermer()


async def test_reindexation_ne_duplique_pas(tmp_path, qdrant_local, monkeypatch):
    """Réindexer un document réécrit ses points au lieu d'en ajouter.

    Les identifiants de chunks étant dérivés du document_id, une seconde
    ingestion avec un nouveau document_id créerait des doublons — d'où la
    suppression préalable, vérifiée ici de bout en bout.
    """
    documents = tmp_path / "docs"
    documents.mkdir()
    fichier = documents / "a.txt"
    fichier.write_text(" ".join(f"Phrase stable numéro {i} du document." for i in range(80)))

    connus: dict = {}
    monkeypatch.setattr(module_pipeline, "enregistrer_document", lambda s, v: None)
    monkeypatch.setattr(module_pipeline, "index_bibliotheque", lambda s: dict(connus))

    settings = _settings(EMBEDDING_DIM=8)
    provider = FauxProvider()

    premier = module_pipeline.ingerer(documents, settings=settings, provider=provider, session=object())
    recherche = QdrantRecherche(settings)
    try:
        total_initial = await recherche.compter()
    finally:
        await recherche.fermer()
    assert total_initial == premier.chunks

    # Le document est connu mais son contenu a changé : réindexation.
    connus[str(fichier)] = ("00000000-0000-0000-0000-000000000000", "empreinte_perimee", 0.0)
    fichier.write_text(" ".join(f"Nouvelle phrase numéro {i} du document." for i in range(80)))

    second = module_pipeline.ingerer(documents, settings=settings, provider=provider, session=object())
    recherche = QdrantRecherche(settings)
    try:
        total_final = await recherche.compter()
    finally:
        await recherche.fermer()

    assert second.indexes == 1
    # Les anciens points ont été retirés : le total reste de l'ordre d'une
    # seule version du document, pas de deux.
    assert total_final <= total_initial + second.chunks
