"""Parseurs de documents.

Chaque module expose la même fonction ``parser(chemin) -> (blocs, infos)`` :
un générateur de :class:`app.ingestion.chunker.Bloc` et un dictionnaire de
métadonnées. Ce contrat unique permet au dispatcher (``app/ingestion/parser.py``)
de traiter tous les formats sans condition, et d'ajouter un format sans
toucher au pipeline.
"""
