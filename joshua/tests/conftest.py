"""Fixtures partagées.

Principe : aucun test n'a besoin de PostgreSQL, de Qdrant, de Redis, d'une
clé Anthropic ni du modèle d'embeddings. Une suite qui exige une
infrastructure n'est pas exécutée — donc elle ne protège de rien.

Les dépendances externes sont remplacées par des doubles minimalistes,
écrits ici pour que chaque test reste lisible.
"""

from __future__ import annotations

import os

import pytest

# Variables obligatoires posées AVANT tout import de app.config : Settings
# refuse de se construire sans elles, et l'import a lieu au chargement des
# modules de test.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test:token")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test")
os.environ.setdefault("ADMIN_TELEGRAM_IDS", "111,222")

from app.config import Settings, get_settings  # noqa: E402
from app.vectorstore.qdrant import ResultatRecherche  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


class FauxProvider:
    """Fournisseur d'embeddings déterministe.

    Le vecteur est dérivé du texte : deux textes identiques donnent le même
    vecteur, deux textes différents en donnent de différents. C'est tout ce
    dont les tests ont besoin, et cela évite de charger un modèle de 1 Go.
    """

    dimension = 8
    model_id = "faux-modele"

    def __init__(self) -> None:
        self.appels = 0

    def _vecteur(self, texte: str) -> list[float]:
        graine = sum(ord(c) for c in texte)
        return [((graine + i * 7) % 100) / 100 for i in range(self.dimension)]

    def embed_documents(self, textes):
        self.appels += 1
        return [self._vecteur(t) for t in textes]

    def embed_query(self, texte):
        self.appels += 1
        return self._vecteur(texte)

    async def aembed_query(self, texte):
        return self.embed_query(texte)

    async def aembed_documents(self, textes):
        return self.embed_documents(list(textes))


class FausseRecherche:
    """Double de QdrantRecherche, avec des résultats programmés."""

    def __init__(self, resultats: list[ResultatRecherche] | None = None) -> None:
        self.resultats = resultats or []
        self.derniers_filtres = None
        self.derniere_limite = None

    async def rechercher(self, vecteur, limite, filtres=None, score_min=None, collection=None):
        self.derniers_filtres = filtres
        self.derniere_limite = limite
        retenus = self.resultats
        if score_min is not None:
            retenus = [r for r in retenus if r.score >= score_min]
        return retenus[:limite]

    async def compter(self, collection=None):
        return len(self.resultats)

    async def sante(self):
        return True

    async def fermer(self):
        return None


@pytest.fixture
def provider() -> FauxProvider:
    return FauxProvider()


def resultat(
    chunk_id: str = "c1",
    document_id: str = "d1",
    score: float = 0.9,
    text: str = "contenu",
    filename: str = "livre.pdf",
    page: int | None = 12,
    **payload,
) -> ResultatRecherche:
    return ResultatRecherche(
        chunk_id=chunk_id,
        document_id=document_id,
        score=score,
        text=text,
        payload={"filename": filename, "page": page, **payload},
    )
