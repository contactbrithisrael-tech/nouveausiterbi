"""Sélection des sources du corpus RBI.

Ce qui est testé ici n'est pas l'ingestion (couverte ailleurs) mais la
DÉCISION : quel dossier est retenu, et que contient-il. C'est le point où un
import « RBI » peut silencieusement se remplir de fichiers de projet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import import_rbi  # noqa: E402


@pytest.fixture
def faux_depot(tmp_path, monkeypatch):
    """Reproduit la disposition réelle : un projet dans un dépôt de site."""
    depot = tmp_path / "site"
    projet = depot / "joshua"
    (projet / "data" / "incoming" / "rbi").mkdir(parents=True)

    # Documents publiés à la racine du dépôt
    (depot / "Constitution_RBI.pdf").write_bytes(b"%PDF-1.4 contenu")
    (depot / "Fiche_Adhesion.pdf").write_bytes(b"%PDF-1.4 contenu")
    # Fichiers de projet, qui ne sont PAS des documents
    (depot / "package.json").write_text("{}")
    (depot / "structure.txt").write_text("arborescence")
    (depot / "README.md").write_text("# site")
    (depot / "assets").mkdir()
    (depot / "assets" / "config.js").write_text("var x = 1;")
    (depot / "assets" / "donnees.json").write_text("{}")

    monkeypatch.setattr(import_rbi, "RACINE_PROJET", projet)
    monkeypatch.delenv("JOSHUA_RBI_SOURCE", raising=False)
    return depot, projet


def test_repli_sur_le_depot_ne_retient_que_les_documents(faux_depot):
    depot, _ = faux_depot
    sources = import_rbi.localiser_sources(None)
    assert sources == [depot]

    trouves = {f.chemin_relatif for f in import_rbi._scanner(depot)}
    assert trouves == {"Constitution_RBI.pdf", "Fiche_Adhesion.pdf"}
    assert not any(nom.endswith((".json", ".txt", ".md", ".js")) for nom in trouves)


def test_dossier_dedie_prioritaire_et_non_restreint(faux_depot):
    """Un dossier explicitement dédié est parcouru sans restriction."""
    _, projet = faux_depot
    dedie = projet / "data" / "incoming" / "rbi"
    (dedie / "rituel.pdf").write_bytes(b"%PDF")
    (dedie / "notes.md").write_text("# notes internes")
    (dedie / "sous").mkdir()
    (dedie / "sous" / "annexe.docx").write_bytes(b"PK")

    assert import_rbi.localiser_sources(None) == [dedie]
    trouves = {f.chemin_relatif for f in import_rbi._scanner(dedie)}
    assert trouves == {"rituel.pdf", "notes.md", "sous/annexe.docx"}


def test_source_explicite_gagne(faux_depot, tmp_path):
    ailleurs = tmp_path / "ailleurs"
    ailleurs.mkdir()
    (ailleurs / "traite.pdf").write_bytes(b"%PDF")
    assert import_rbi.localiser_sources(str(ailleurs)) == [ailleurs]


def test_variable_denvironnement(faux_depot, tmp_path, monkeypatch):
    ailleurs = tmp_path / "env"
    ailleurs.mkdir()
    (ailleurs / "livre.epub").write_bytes(b"PK")
    monkeypatch.setenv("JOSHUA_RBI_SOURCE", str(ailleurs))
    assert import_rbi.localiser_sources(None) == [ailleurs]


def test_aucune_source_utilisable(tmp_path, monkeypatch):
    """Un dépôt sans document ne doit pas retourner un dossier vide « valide »."""
    depot = tmp_path / "vide"
    projet = depot / "joshua"
    projet.mkdir(parents=True)
    (depot / "package.json").write_text("{}")
    monkeypatch.setattr(import_rbi, "RACINE_PROJET", projet)
    monkeypatch.delenv("JOSHUA_RBI_SOURCE", raising=False)
    assert import_rbi.localiser_sources(None) == []


def test_conventions_du_corpus_stables():
    """Ces valeurs pilotent les filtres Qdrant : les changer casse les filtres
    des documents déjà indexés."""
    assert import_rbi.CATEGORIE == "rbi"
    assert import_rbi.SOURCE == "rbi_officiel"
    assert import_rbi.TAGS == ["rbi", "officiel"]


def test_inventaire_et_import_partagent_les_memes_regles(faux_depot):
    """Le piège que ce test verrouille : un aperçu restreint suivi d'un import
    qui ne l'est pas. L'inventaire annonçait trois documents, l'ingestion en
    avalait deux cents — dont le package.json du dépôt."""
    depot, _ = faux_depot
    regles = import_rbi.regles_de_scan(depot)
    assert regles["extensions"] == import_rbi.EXTENSIONS_DEPOT
    assert regles["profondeur_max"] == 0

    from app.ingestion.loader import parcourir

    vus_inventaire = {f.chemin_relatif for f in import_rbi._scanner(depot)}
    vus_ingestion = {f.chemin_relatif for f in parcourir(depot, **regles)}
    assert vus_inventaire == vus_ingestion


def test_ingerer_accepte_les_regles_de_scan(faux_depot, monkeypatch):
    """`ingerer` doit réellement transmettre les règles à `parcourir`."""
    from app.config import Settings, get_settings
    from app.ingestion import pipeline as module_pipeline

    depot, _ = faux_depot
    vus: list[str] = []
    monkeypatch.setattr(module_pipeline, "assurer_collection", lambda *a, **k: "c")
    monkeypatch.setattr(module_pipeline, "index_bibliotheque", lambda s: {})
    monkeypatch.setattr(module_pipeline, "enregistrer_document", lambda s, v: vus.append(v["filename"]))
    monkeypatch.setattr(module_pipeline, "upsert_batch", lambda *a, **k: 0)

    get_settings.cache_clear()
    settings = Settings(TELEGRAM_BOT_TOKEN="t", ANTHROPIC_API_KEY="k")

    class Encodeur:
        dimension, model_id = 4, "faux"

        def embed_documents(self, textes):
            return [[0.1, 0.2, 0.3, 0.4] for _ in textes]

    compteurs = module_pipeline.ingerer(
        depot, settings=settings, provider=Encodeur(), session=object(),
        **import_rbi.regles_de_scan(depot),
    )
    assert compteurs.vus == 2  # les deux PDF, pas package.json ni assets/
