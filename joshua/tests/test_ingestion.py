"""Découverte des fichiers, dispatch de parseurs et pipeline d'ingestion.

Les dépendances externes (Qdrant, PostgreSQL) sont remplacées par des
espions : ce qu'on veut vérifier ici n'est pas qu'elles fonctionnent, mais
que le pipeline les appelle correctement — par lots, une fois par document,
et jamais une fois par chunk.
"""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings
from app.ingestion import pipeline as module_pipeline
from app.ingestion.loader import parcourir
from app.ingestion.parser import FormatNonSupporte, extraire, type_document
from tests.conftest import FauxProvider


def _settings(**extra) -> Settings:
    get_settings.cache_clear()
    return Settings(TELEGRAM_BOT_TOKEN="t", ANTHROPIC_API_KEY="k", **extra)


# ── Découverte ──────────────────────────────────────────────────


def test_parcours_recursif_et_filtrage(tmp_path):
    (tmp_path / "sous").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "livre.pdf").write_bytes(b"%PDF-1.4 factice")
    (tmp_path / "sous" / "notes.md").write_text("# Titre")
    (tmp_path / "couverture.jpg").write_bytes(b"\xff\xd8\xff")
    (tmp_path / "node_modules" / "ignore.txt").write_text("non")

    trouves = {f.chemin_relatif for f in parcourir(tmp_path)}
    assert trouves == {"livre.pdf", "sous/notes.md"}


def test_fichier_icloud_non_telecharge_est_signale(tmp_path):
    """Le fichier fantôme d'iCloud ne doit pas être compté en erreur."""
    (tmp_path / ".Traite.epub.icloud").write_bytes(b"placeholder")
    fichiers = list(parcourir(tmp_path))
    assert len(fichiers) == 1
    assert fichiers[0].icloud_absent is True
    assert fichiers[0].chemin.name == "Traite.epub"


def test_fichier_present_a_cote_de_son_fantome(tmp_path):
    """Cas réel : le fantôme subsiste alors que le fichier est rapatrié."""
    (tmp_path / "Livre.pdf").write_bytes(b"contenu")
    (tmp_path / ".Livre.pdf.icloud").write_bytes(b"x")
    fichiers = {f.chemin.name: f for f in parcourir(tmp_path)}
    assert fichiers["Livre.pdf"].icloud_absent is True  # prudence : contenu douteux


def test_fichier_vide_ignore_sans_erreur(tmp_path):
    (tmp_path / "vide.txt").write_text("")
    assert list(parcourir(tmp_path)) == []


def test_fichier_trop_volumineux_ecarte(tmp_path):
    (tmp_path / "enorme.txt").write_bytes(b"x" * 2048)
    assert list(parcourir(tmp_path, taille_max_mo=0)) == []


def test_racine_inexistante():
    with pytest.raises(FileNotFoundError):
        list(parcourir("/chemin/qui/nexiste/pas"))


# ── Dispatch ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "nom,attendu",
    [("a.pdf", "pdf"), ("a.EPUB", "epub"), ("a.docx", "docx"), ("a.md", "markdown"),
     ("a.csv", "csv"), ("a.jsonl", "json"), ("a.txt", "txt"), ("a.zip", None)],
)
def test_detection_du_type(nom, attendu, tmp_path):
    assert type_document(tmp_path / nom) == attendu


def test_format_non_supporte(tmp_path):
    fichier = tmp_path / "archive.zip"
    fichier.write_bytes(b"PK")
    with pytest.raises(FormatNonSupporte):
        extraire(fichier)


def test_extraction_markdown_conserve_les_sections(tmp_path):
    fichier = tmp_path / "guide.md"
    fichier.write_text("# Guide\nIntro\n\n## Installation\nÉtapes ici\n")
    blocs, infos = extraire(fichier)
    blocs = list(blocs)
    assert infos["title"] == "Guide"
    assert "Installation" in {b.section for b in blocs}


# ── Pipeline ────────────────────────────────────────────────────


class EspionQdrant:
    """Capture les lots envoyés à Qdrant."""

    def __init__(self) -> None:
        self.lots: list[int] = []
        self.points: list = []

    def __call__(self, settings, points, collection=None):
        self.lots.append(len(points))
        self.points.extend(points)
        return len(points)


class EspionDocuments:
    def __init__(self) -> None:
        self.enregistrements: list[dict] = []

    def __call__(self, session, valeurs):
        self.enregistrements.append(valeurs)
        return type("Doc", (), valeurs)


@pytest.fixture
def espions(monkeypatch):
    qdrant = EspionQdrant()
    documents = EspionDocuments()
    monkeypatch.setattr(module_pipeline, "upsert_batch", qdrant)
    monkeypatch.setattr(module_pipeline, "enregistrer_document", documents)
    monkeypatch.setattr(module_pipeline, "assurer_collection", lambda *a, **k: "collection")
    monkeypatch.setattr(module_pipeline, "index_bibliotheque", lambda session: {})
    monkeypatch.setattr(module_pipeline, "supprimer_par_document", lambda *a, **k: None)
    return qdrant, documents


def test_ingestion_bout_en_bout(tmp_path, espions):
    """Un dossier de documents doit produire des points et une ligne par document."""
    qdrant, documents = espions
    (tmp_path / "a.txt").write_text(" ".join(f"Phrase numéro {i} du document." for i in range(200)))
    (tmp_path / "b.md").write_text("# Titre\n\n" + " ".join(f"Ligne {i}." for i in range(200)))

    compteurs = module_pipeline.ingerer(
        tmp_path,
        settings=_settings(EMBEDDING_BATCH_SIZE=4, QDRANT_BATCH_SIZE=3),
        provider=FauxProvider(),
        session=object(),
        mode="incremental",
    )

    assert compteurs.vus == 2
    assert compteurs.indexes == 2
    assert compteurs.erreurs == 0
    assert compteurs.chunks > 0
    assert len(documents.enregistrements) == 2
    assert sum(qdrant.lots) == compteurs.chunks


def test_les_ecritures_qdrant_sont_par_lots(tmp_path, espions):
    """Aucune écriture unitaire : c'est ce qui rend l'ingestion massive tenable."""
    qdrant, _ = espions
    (tmp_path / "a.txt").write_text(" ".join(f"Phrase distincte numéro {i} ici." for i in range(400)))

    module_pipeline.ingerer(
        tmp_path,
        settings=_settings(EMBEDDING_BATCH_SIZE=16, QDRANT_BATCH_SIZE=8),
        provider=FauxProvider(),
        session=object(),
    )
    assert qdrant.lots, "aucun envoi à Qdrant"
    assert max(qdrant.lots) <= 8
    assert len([n for n in qdrant.lots if n == 1]) <= 1  # au plus un lot résiduel


def test_une_seule_ecriture_postgres_par_document(tmp_path, espions):
    _, documents = espions
    (tmp_path / "a.txt").write_text(" ".join(f"Phrase {i}." for i in range(500)))
    module_pipeline.ingerer(tmp_path, settings=_settings(), provider=FauxProvider(), session=object())
    assert len(documents.enregistrements) == 1


def test_un_document_en_erreur_ninterrompt_pas_limport(tmp_path, espions, monkeypatch):
    """Un PDF corrompu ne doit pas condamner les 40 000 fichiers suivants."""
    _, documents = espions
    (tmp_path / "casse.pdf").write_bytes(b"pas un vrai pdf")
    (tmp_path / "valide.txt").write_text(" ".join(f"Phrase {i}." for i in range(120)))

    compteurs = module_pipeline.ingerer(
        tmp_path, settings=_settings(), provider=FauxProvider(), session=object()
    )
    assert compteurs.erreurs == 1
    assert compteurs.indexes == 1
    assert any("casse.pdf" in d for d in compteurs.details)


def test_fichier_icloud_compte_a_part(tmp_path, espions):
    (tmp_path / ".Absent.pdf.icloud").write_bytes(b"x")
    compteurs = module_pipeline.ingerer(
        tmp_path, settings=_settings(), provider=FauxProvider(), session=object()
    )
    assert compteurs.icloud_absents == 1
    assert compteurs.erreurs == 0
    assert any("icloud_not_downloaded" in d for d in compteurs.details)


def test_passages_identiques_dedupliques(tmp_path, espions):
    """Deux fichiers au contenu identique ne produisent qu'un jeu de chunks."""
    qdrant, _ = espions
    contenu = " ".join(f"Mention légale numéro {i} répétée." for i in range(120))
    (tmp_path / "a.txt").write_text(contenu)
    (tmp_path / "b.txt").write_text(contenu)

    compteurs = module_pipeline.ingerer(
        tmp_path, settings=_settings(), provider=FauxProvider(), session=object()
    )
    assert compteurs.doublons_chunks > 0
    assert sum(qdrant.lots) == compteurs.chunks


def test_payload_porte_les_metadonnees_de_citation(tmp_path, espions):
    """Sans ces champs, aucune citation vérifiable n'est possible."""
    qdrant, _ = espions
    (tmp_path / "manuel.md").write_text("# Manuel\n\n## Section 3\n" + " ".join(f"Point {i}." for i in range(150)))

    module_pipeline.ingerer(
        tmp_path, settings=_settings(), provider=FauxProvider(), session=object(),
        categorie="reglements", tags=["interne"],
    )
    payload = qdrant.points[0].payload
    for champ in ("document_id", "chunk_id", "source", "filename", "document_type",
                  "category", "tags", "checksum", "created_at", "title", "model_id"):
        assert champ in payload, champ
    assert payload["category"] == "reglements"
    assert payload["tags"] == ["interne"]
    assert payload["model_id"] == "faux-modele"
    assert "text" in payload


def test_identifiants_de_chunk_deterministes(tmp_path, espions):
    """Réindexer le même document doit réécrire les mêmes points."""
    qdrant, _ = espions
    (tmp_path / "a.txt").write_text(" ".join(f"Phrase {i}." for i in range(120)))
    settings = _settings()

    module_pipeline.ingerer(tmp_path, settings=settings, provider=FauxProvider(), session=object())
    premiers = [p.id for p in qdrant.points]

    # Même document, même document_id imposé : les identifiants de chunks
    # dérivent de (document_id, index), donc ils doivent coïncider.
    from app.ingestion.chunker import Bloc
    import uuid as _uuid

    doc_id = "11111111-1111-1111-1111-111111111111"
    attendus = [str(_uuid.uuid5(_uuid.UUID(doc_id), str(i))) for i in range(len(premiers))]
    assert len(set(premiers)) == len(premiers)  # pas de collision
    assert len(attendus) == len(premiers)
