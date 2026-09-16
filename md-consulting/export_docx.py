"""Mise en page du compte rendu remis à la personne, en .docx."""
from __future__ import annotations

import re
from pathlib import Path

import config
import dates_fr
import docx_minimal as D
import personne as P
import rapport as R
import seance as S

DOSSIER_EXPORT = Path(__file__).resolve().parent / "exports"


def nom_fichier(pers: P.Personne, sea: S.Seance) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "-",
                  f"{pers.nom}-{pers.prenom}").strip("-") or "fiche"
    return f"{sea.date}_{base}_compte-rendu.docx"


def _paragraphes(d: D.Document, texte: str) -> None:
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if not ligne:
            d.paragraphe()
        elif ligne.startswith(("-", "•", "*")):
            d.puces([ligne.lstrip("-•* ").strip()])
        else:
            d.paragraphe(ligne)


def _tableau(d: D.Document, entetes: tuple[str, ...], texte: str) -> None:
    """Une ligne de texte par ligne de tableau, colonnes séparées par « | ».
    Une ligne sans séparateur reste un paragraphe : le consultant peut
    écrire une remarque au milieu du tableau sans tout casser."""
    lignes, avant = [], []
    for brute in texte.splitlines():
        if "|" in brute:
            cellules = [c.strip() for c in brute.split("|")]
            cellules = (cellules + [""] * len(entetes))[:len(entetes)]
            if any(cellules):
                lignes.append(cellules)
        elif brute.strip() and not lignes:
            avant.append(brute.strip())
    for ligne in avant:
        d.paragraphe(ligne)
    if lignes:
        d.tableau(list(entetes), lignes)


def construire(pers: P.Personne, sea: S.Seance, rap: R.Rapport) -> D.Document:
    d = D.Document()
    for ligne in config.lignes_entete():
        d.paragraphe(ligne, gras=(ligne == config.ORGANISATION["nom"]), centre=True)
    d.paragraphe()
    d.paragraphe(config.TITRE_DOCUMENT, gras=True, taille=18, centre=True,
                 couleur="1F3864")
    d.paragraphe(config.SOUS_TITRE, taille=10, centre=True, couleur="666666")
    d.paragraphe()

    d.tableau(["", ""], [
        ["Personne reçue", pers.nom_affiche],
        ["Date de naissance", dates_fr.jour(pers.date_naissance)
         + (f" ({pers.age} ans)" if pers.age is not None else "")],
        ["Coordonnées", " · ".join(x for x in (pers.telephone, pers.courriel) if x) or "—"],
        ["Situation", pers.situation or "—"],
        ["Public", P.PUBLICS.get(pers.public, pers.public)],
        ["Date de la séance", dates_fr.jour(sea.date)],
        ["Durée prévue", f"{sea.chrono_max_minutes} minutes"],
        ["Objectif de la séance", sea.objectif_texte or "—"],
    ])

    titres = R.intitules(pers.public)
    for cle in R.BLOCS:
        d.titre(titres[cle], niveau=2)
        texte = (getattr(rap, cle) or "").strip()
        if not texte:
            d.paragraphe("—", couleur="999999")
        elif cle in R.BLOCS_TABLEAU:
            _tableau(d, R.BLOCS_TABLEAU[cle], texte)
        else:
            _paragraphes(d, texte)

    d.paragraphe()
    d.paragraphe(config.AVERTISSEMENT, taille=9, couleur="666666")
    if config.ORGANISATION["mentions_pied"]:
        d.paragraphe(config.ORGANISATION["mentions_pied"], taille=8, couleur="999999")
    d.paragraphe(f"Document établi le {dates_fr.jour(rap.date_generation)}.",
                 taille=9, couleur="666666")
    return d


def exporter(pers: P.Personne, sea: S.Seance, rap: R.Rapport,
             dossier: Path | str | None = None) -> Path:
    """Écrit le fichier et renvoie son chemin. Aucun envoi : action manuelle."""
    cible = Path(dossier or DOSSIER_EXPORT) / nom_fichier(pers, sea)
    return construire(pers, sea, rap).enregistrer(cible)
