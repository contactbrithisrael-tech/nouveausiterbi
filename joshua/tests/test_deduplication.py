"""Empreintes et déduplication."""

from __future__ import annotations

import pytest

from app.ingestion.deduplication import (
    DeduplicateurChunks,
    checksum_fichier,
    checksum_texte,
    fichier_inchange,
)


def test_checksum_fichier_stable(tmp_path):
    fichier = tmp_path / "livre.txt"
    fichier.write_bytes(b"contenu du livre" * 5000)
    empreinte = checksum_fichier(fichier)
    assert len(empreinte) == 64
    assert empreinte == checksum_fichier(fichier)


def test_checksum_fichier_par_blocs(tmp_path):
    """Le hachage en flux doit donner le même résultat qu'en une fois.

    C'est ce qui autorise à hacher un PDF de 2 Go avec 1 Mio de mémoire.
    """
    fichier = tmp_path / "gros.bin"
    fichier.write_bytes(b"x" * (3 * 1024 * 1024 + 17))
    assert checksum_fichier(fichier, taille_bloc=1024) == checksum_fichier(fichier, taille_bloc=1024 * 1024)


def test_checksum_detecte_modification(tmp_path):
    fichier = tmp_path / "a.txt"
    fichier.write_text("version 1")
    avant = checksum_fichier(fichier)
    fichier.write_text("version 2")
    assert checksum_fichier(fichier) != avant


def test_checksum_texte_ignore_la_mise_en_forme():
    """Deux extractions du même passage diffèrent par les espaces."""
    assert checksum_texte("Bonjour   le\tmonde") == checksum_texte("Bonjour le monde")
    assert checksum_texte("Bonjour") != checksum_texte("Bonsoir")


def test_deduplicateur_filtre_les_repetitions():
    dedup = DeduplicateurChunks()
    assert dedup.est_nouveau("Mentions légales de l'éditeur.")
    assert not dedup.est_nouveau("Mentions légales de l'éditeur.")
    assert not dedup.est_nouveau("Mentions   légales de l'éditeur.")  # après normalisation
    assert dedup.est_nouveau("Un autre passage.")
    assert dedup.doublons == 2
    assert dedup.taille == 2


def test_deduplicateur_se_desactive_quand_sature():
    """La saturation dégrade le service sans jamais l'interrompre."""
    dedup = DeduplicateurChunks(max_entrees=2)
    dedup.est_nouveau("a")
    dedup.est_nouveau("b")
    assert dedup.est_nouveau("a") is True  # filtre désactivé, plus de rejet


def test_fichier_inchange_par_mtime(tmp_path):
    fichier = tmp_path / "a.txt"
    fichier.write_text("contenu")
    empreinte = checksum_fichier(fichier)
    mtime = fichier.stat().st_mtime
    assert fichier_inchange(fichier, empreinte, mtime) is True


def test_fichier_inchange_verifie_le_contenu_si_mtime_different(tmp_path):
    """Un mtime réécrit par une synchronisation ne doit pas forcer un import."""
    fichier = tmp_path / "a.txt"
    fichier.write_text("contenu")
    empreinte = checksum_fichier(fichier)
    assert fichier_inchange(fichier, empreinte, mtime_connu=0.0) is True
    assert fichier_inchange(fichier, "autre_empreinte", mtime_connu=0.0) is False


def test_fichier_inconnu_est_a_indexer(tmp_path):
    fichier = tmp_path / "a.txt"
    fichier.write_text("x")
    assert fichier_inchange(fichier, None, None) is False
