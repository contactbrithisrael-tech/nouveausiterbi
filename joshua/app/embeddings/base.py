"""Abstraction des fournisseurs d'embeddings.

Choix d'architecture
--------------------
* **Une interface, plusieurs implémentations.** Le reste du code ne connaît
  que ``EmbeddingProvider``. Changer de fournisseur (FastEmbed → Voyage)
  n'impose aucune modification dans le RAG ni dans l'ingestion.

* **Distinction document / requête.** Les modèles de la famille E5 exigent
  des préfixes différents (« passage: » et « query: ») ; les ignorer coûte
  plusieurs points de rappel. L'interface impose donc deux méthodes plutôt
  qu'une seule ``embed()`` — c'est la seule façon de rendre cette contrainte
  visible au niveau du type, et non enfouie dans une implémentation.

* **Traitement par lots imposé.** Les signatures acceptent des séquences :
  encoder million de chunks un par un serait des ordres de grandeur plus
  lent, et l'API rend cette erreur difficile à commettre.

* **Changer de modèle invalide l'index.** La dimension et la géométrie de
  l'espace vectoriel changent : ``model_id`` est stocké dans le payload
  Qdrant afin qu'une incohérence soit détectable (voir vectorstore/qdrant.py).
"""

from __future__ import annotations

import abc
import asyncio
from typing import Sequence


class EmbeddingProvider(abc.ABC):
    """Contrat commun à tous les fournisseurs."""

    #: Dimension des vecteurs produits. Doit correspondre à la collection.
    dimension: int
    #: Identifiant du modèle, écrit dans le payload de chaque point.
    model_id: str

    @abc.abstractmethod
    def embed_documents(self, textes: Sequence[str]) -> list[list[float]]:
        """Encode des passages destinés à être indexés."""

    @abc.abstractmethod
    def embed_query(self, texte: str) -> list[float]:
        """Encode une question d'utilisateur."""

    async def aembed_query(self, texte: str) -> list[float]:
        """Version asynchrone.

        L'implémentation par défaut délègue à un thread : FastEmbed est
        synchrone et gourmand en CPU ; l'appeler directement depuis la boucle
        asyncio bloquerait TOUS les utilisateurs du bot pendant l'encodage.
        Un fournisseur réellement asynchrone (API distante) surcharge cette
        méthode.
        """
        return await asyncio.to_thread(self.embed_query, texte)

    async def aembed_documents(self, textes: Sequence[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_documents, list(textes))


def get_embedding_provider(settings) -> EmbeddingProvider:
    """Fabrique. Les imports sont faits ICI, pas au chargement du module.

    FastEmbed tire onnxruntime et télécharge un modèle au premier usage :
    l'importer au niveau du module ferait payer ce coût à tout processus
    important n'importe quelle partie de l'application — y compris la suite
    de tests, qui n'en a pas besoin.
    """
    nom = settings.EMBEDDING_PROVIDER
    if nom == "fastembed":
        from app.embeddings.fastembed_provider import FastEmbedProvider

        return FastEmbedProvider(
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIM,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
        )
    raise ValueError(
        f"Fournisseur d'embeddings « {nom} » non implémenté. "
        "Ajouter une classe dans app/embeddings/ et l'enregistrer ici."
    )
