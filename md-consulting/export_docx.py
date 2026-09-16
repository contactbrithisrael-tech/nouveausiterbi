"""Mise en page du compte rendu remis à la personne, en .docx."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import config
import docx_minimal as D
import personne as P
import rapport as R
import seance as S

DOSSIER_EXPORT = Path(__file__).resolve().parent / "exports"


def _jour(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


def nom_fichier(pers: P.Personne, sea: S.Seance) -> str:
    """Le nom du fichier porte le pseudonyme, jamais le nom complet :
    une liste de répertoire ne doit rien révéler."""
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", pers.pseudonyme).strip("-") or "fiche"
    return f"{sea.date}_{base}_compte-rendu.docx"


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
        ["Personne reçue", pers.nom_complet or pers.pseudonyme],
        ["Public", P.PUBLICS.get(pers.public, pers.public)],
        ["Date de la séance", _jour(sea.date)],
        ["Durée prévue", f"{sea.chrono_max_minutes} minutes"],
        ["Objectif de la séance", sea.objectif_texte or "—"],
    ])

    titres = R.intitules(pers.public)
    for cle in R.BLOCS:
        d.titre(titres[cle], niveau=2)
        texte = (getattr(rap, cle) or "").strip()
        if not texte:
            d.paragraphe("—", couleur="999999")
            continue
        for ligne in texte.splitlines():
            ligne = ligne.strip()
            if not ligne:
                d.paragraphe()
            elif ligne.startswith(("-", "•", "*")):
                d.puces([ligne.lstrip("-•* ").strip()])
            else:
                d.paragraphe(ligne)

    d.paragraphe()
    d.paragraphe(config.AVERTISSEMENT, taille=9, couleur="666666")
    if config.ORGANISATION["mentions_pied"]:
        d.paragraphe(config.ORGANISATION["mentions_pied"], taille=8, couleur="999999")
    d.paragraphe(f"Document établi le {_jour(rap.date_generation)}.",
                 taille=9, couleur="666666")
    return d


def exporter(pers: P.Personne, sea: S.Seance, rap: R.Rapport,
             dossier: Path | str | None = None) -> Path:
    """Écrit le fichier et renvoie son chemin. Aucun envoi : action manuelle."""
    cible = Path(dossier or DOSSIER_EXPORT) / nom_fichier(pers, sea)
    return construire(pers, sea, rap).enregistrer(cible)
