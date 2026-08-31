"""Découpage : taille, recouvrement, frontières de phrase, métadonnées."""

from __future__ import annotations

from app.ingestion.chunker import Bloc, chunker_blocs, decouper_en_phrases


def test_phrases_simples():
    phrases = decouper_en_phrases("Une phrase. Une autre ! Et une dernière ?")
    assert phrases == ["Une phrase.", "Une autre !", "Et une dernière ?"]


def test_abreviations_ne_coupent_pas():
    """« M. Dupont » et « p. 42 » ne sont pas des fins de phrase.

    C'est le piège classique d'un découpage par ponctuation : sans protection,
    un corpus français produit des chunks tronqués tous les deux paragraphes.
    """
    assert decouper_en_phrases("M. Dupont arrive. Il repart.") == [
        "M. Dupont arrive.",
        "Il repart.",
    ]
    assert len(decouper_en_phrases("Voir p. 42 puis revenir. Fin.")) == 2
    assert len(decouper_en_phrases("J. Dupont écrit. Puis part.")) == 2


def test_taille_respectee():
    blocs = [Bloc(texte="Phrase de test numéro %d avec du contenu. " % i * 4) for i in range(30)]
    chunks = list(chunker_blocs(blocs, taille_cible=500, recouvrement=100, taille_min=50))
    assert chunks
    # Tolérance : une phrase entière est toujours conservée, ce qui peut
    # dépasser légèrement la cible. C'est le comportement voulu.
    assert all(c.taille <= 500 * 1.2 for c in chunks)


def test_recouvrement_present():
    """La fin d'un chunk doit réapparaître au début du suivant."""
    texte = " ".join(f"Phrase unique numéro {i} de ce document." for i in range(60))
    chunks = list(chunker_blocs([Bloc(texte=texte)], taille_cible=400, recouvrement=120, taille_min=50))
    assert len(chunks) >= 2
    mots_fin = set(chunks[0].texte.split()[-8:])
    mots_debut = set(chunks[1].texte.split()[:20])
    assert mots_fin & mots_debut, "aucun recouvrement entre deux chunks consécutifs"


def test_aucune_coupure_en_milieu_de_phrase():
    texte = " ".join(f"Voici la phrase numéro {i} du document de test." for i in range(40))
    chunks = list(chunker_blocs([Bloc(texte=texte)], taille_cible=300, recouvrement=60, taille_min=40))
    for chunk in chunks:
        assert chunk.texte.endswith((".", "!", "?", "…")), chunk.texte[-40:]


def test_metadonnees_conservees():
    blocs = [
        Bloc(texte="Contenu de la première page. " * 20, page=1, section="Introduction", title="Livre"),
        Bloc(texte="Contenu de la seconde page. " * 20, page=2, section="Chapitre 1", title="Livre"),
    ]
    chunks = list(chunker_blocs(blocs, taille_cible=300, recouvrement=50, taille_min=40))
    assert all(c.title == "Livre" for c in chunks)
    assert {c.page for c in chunks} == {1, 2}
    assert "Introduction" in {c.section for c in chunks}


def test_phrase_gigantesque_est_coupee():
    """Un PDF mal extrait produit des « phrases » sans ponctuation.

    Sans découpe de dernier recours, un tel bloc formerait un chunk unique de
    plusieurs milliers de caractères, inutilisable pour le RAG.
    """
    texte = "mot " * 3000  # aucune ponctuation
    chunks = list(chunker_blocs([Bloc(texte=texte)], taille_cible=400, recouvrement=50, taille_min=40))
    assert len(chunks) > 1
    assert all(c.taille <= 500 for c in chunks)


def test_document_vide_ne_produit_rien():
    assert list(chunker_blocs([Bloc(texte="   ")], 400, 50, 40)) == []


def test_index_incremental():
    texte = " ".join(f"Phrase {i} du document." for i in range(80))
    chunks = list(chunker_blocs([Bloc(texte=texte)], 300, 50, 40))
    assert [c.index for c in chunks] == list(range(len(chunks)))
