"""Identité imprimée en tête des rapports.

Les valeurs sont VIDES à dessein. Le document de référence fourni portait les
mentions de LinkOm Consultants (Qualiopi, SIRET, DIRECCTE) : ces numéros
engagent un organisme certifié et ne sont pas recopiés ici. Un champ laissé
vide n'est tout simplement pas imprimé.

⚠ Le compte rendu produit par cet outil n'est PAS une synthèse de bilan de
compétences au sens des articles R6313-4 à R6313-8 du code du travail. Il ne
doit ni viser ces articles, ni porter un numéro de certification, sous peine
de ressembler à un document réglementaire sans en être un.
"""
from __future__ import annotations

ORGANISATION = {
    "nom": "MD Consulting",
    "consultant": "",          # ex. "Mickaël DARMON"
    "site": "",
    "courriel": "",
    "telephone": "",
    "mentions_pied": "",       # ligne libre de bas de page, si nécessaire
}

TITRE_DOCUMENT = "Compte rendu de séance de conseil"
SOUS_TITRE = "Permanence conseil — orientation, emploi, reconversion"

AVERTISSEMENT = (
    "Ce compte rendu restitue une séance de conseil. Il ne constitue ni un "
    "bilan de compétences, ni un document officiel de France Travail."
)


def lignes_entete() -> list[str]:
    """Lignes d'en-tête réellement renseignées, dans l'ordre d'affichage."""
    o = ORGANISATION
    brutes = [o["nom"], o["consultant"], o["site"], o["courriel"], o["telephone"]]
    return [l.strip() for l in brutes if l and l.strip()]
