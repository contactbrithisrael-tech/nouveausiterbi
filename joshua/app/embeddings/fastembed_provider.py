"""Fournisseur d'embeddings local, basé sur FastEmbed (ONNX).

Pourquoi FastEmbed par défaut
-----------------------------
L'ingestion d'une bibliothèque de livres produit des centaines de milliers
de chunks. Avec un fournisseur facturé à l'appel, le seul import initial
coûterait plusieurs centaines d'euros et interdirait toute réindexation
expérimentale. FastEmbed encode localement sur CPU : l'ingestion devient
gratuite et rejouable, ce qui change complètement la façon de travailler.

Contrepartie assumée : le premier appel télécharge le modèle (~1 Go pour
multilingual-e5-large) et l'encodage est plus lent qu'une API dédiée. Le
modèle est mis en cache dans un volume Docker pour n'être téléchargé qu'une
fois.
"""

from __future__ import annotations

import threading
from typing import Sequence

from app.utils.logging import get_logger

log = get_logger(__name__)

# Préfixes exigés par la famille E5. Sur les modèles qui n'en attendent pas,
# ils dégradent légèrement la qualité — d'où la détection par nom de modèle
# plutôt qu'une application systématique.
_PREFIXES_E5 = ("e5", "multilingual-e5")


class FastEmbedProvider:
    """Encodage local. Le modèle est chargé paresseusement, une seule fois."""

    def __init__(self, model_name: str, dimension: int, batch_size: int = 64) -> None:
        self.model_id = model_name
        self.dimension = dimension
        self._batch_size = batch_size
        self._modele = None
        # Le chargement peut être déclenché par deux threads simultanés (le
        # pool de asyncio.to_thread) : sans verrou, deux instances du modèle
        # seraient chargées en mémoire, soit le double de RAM consommée.
        self._verrou = threading.Lock()
        self._utilise_prefixes = any(p in model_name.lower() for p in _PREFIXES_E5)

    def _get_modele(self):
        if self._modele is None:
            with self._verrou:
                if self._modele is None:  # double vérification sous verrou
                    from fastembed import TextEmbedding  # import tardif : voir base.py

                    log.info("embedding_model_loading", model=self.model_id)
                    self._modele = TextEmbedding(model_name=self.model_id)
                    log.info("embedding_model_loaded", model=self.model_id)
        return self._modele

    def _encoder(self, textes: Sequence[str]) -> list[list[float]]:
        modele = self._get_modele()
        vecteurs = [v.tolist() for v in modele.embed(list(textes), batch_size=self._batch_size)]
        if vecteurs and len(vecteurs[0]) != self.dimension:
            # Incohérence détectée tôt : indexer des vecteurs de la mauvaise
            # dimension produirait une erreur Qdrant obscure, des milliers de
            # points plus tard.
            raise ValueError(
                f"Dimension inattendue : le modèle {self.model_id} produit "
                f"{len(vecteurs[0])} composantes, EMBEDDING_DIM vaut {self.dimension}."
            )
        return vecteurs

    def embed_documents(self, textes: Sequence[str]) -> list[list[float]]:
        if not textes:
            return []
        prepares = [f"passage: {t}" if self._utilise_prefixes else t for t in textes]
        return self._encoder(prepares)

    def embed_query(self, texte: str) -> list[float]:
        prepare = f"query: {texte}" if self._utilise_prefixes else texte
        return self._encoder([prepare])[0]
