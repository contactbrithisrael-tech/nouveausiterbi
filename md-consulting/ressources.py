"""Catalogue des ressources externes (données du Module 5, sans interface).

Règle : uniquement des services publics ou des outils disposant d'un accès
gratuit réel. Chaque entrée porte son statut d'accès et l'état de sa
vérification — rien n'est présenté comme gratuit sans l'avoir établi.

Exclusion volontaire : les tests CentralTest (BF5, VOCATION, e-Stress,
Profil Pro 2) sont des produits sous licence payante, sans version gratuite.
Ils n'ont pas leur place dans une liste remise à une personne reçue.
"""
from __future__ import annotations

from dataclasses import dataclass

# Statuts d'accès
LIBRE = "libre"                  # aucun compte, aucun paiement
COMPTE_REQUIS = "compte requis"  # gratuit, mais inscription obligatoire
FREEMIUM = "freemium"            # socle gratuit utilisable + options payantes
SERVICE_PUBLIC = "service public"


@dataclass(frozen=True)
class Ressource:
    nom: str
    url: str
    description: str
    acces: str
    publics: tuple[str, ...]
    note: str = ""


RESSOURCES: tuple[Ressource, ...] = (
    # ── Intérêts professionnels (RIASEC / Holland) ────────────────────────
    Ressource(
        "Test RIASEC (Holland)", "https://dividendes.ch/test-holland",
        "Questionnaire d'intérêts professionnels. Version IIP RIASEC Markers "
        "(Armstrong, Rounds & Liao, 2008), domaine public.",
        LIBRE, ("college", "lycee", "reconversion", "handicap", "burnout"),
        "Référence de l'instrument fournie par le brief MD Consulting."),
    Ressource(
        "RIASEC — Open Psychometrics", "https://openpsychometrics.org/tests/RIASEC",
        "Même famille d'instrument, en anglais.",
        LIBRE, ("lycee", "reconversion"),
        "Anglais : à réserver aux personnes à l'aise avec la langue."),

    # ── Personnalité (Big Five / IPIP) ────────────────────────────────────
    Ressource(
        "Big Five — IPIP", "https://ipiptest.com",
        "Inventaire de personnalité issu de l'International Personality Item "
        "Pool (Goldberg, Oregon Research Institute), libre de droits.",
        LIBRE, ("lycee", "reconversion", "handicap", "burnout")),
    Ressource(
        "IPIP-NEO-120 en français", "https://adnpersonnalite.com",
        "Version française de l'inventaire IPIP-NEO-120.",
        LIBRE, ("lycee", "reconversion", "handicap", "burnout")),
    Ressource(
        "AssessFirst", "https://assessfirst.com",
        "Évaluation motivations / personnalité / raisonnement. Société privée, "
        "gratuit pour les particuliers.",
        COMPTE_REQUIS, ("reconversion", "vae"),
        "Compte obligatoire : les réponses sont hébergées par un tiers. "
        "À signaler à la personne avant de proposer le lien."),

    # ── Candidature : CV ──────────────────────────────────────────────────
    Ressource(
        "CVDesignR", "https://cvdesignr.com",
        "Création de CV en ligne, export PDF, modèles à mettre en page soi-même. "
        "Éditeur français. Connexion possible avec un compte France Travail pour "
        "importer le profil de compétences.",
        FREEMIUM, ("lycee", "reconversion", "vae", "handicap", "burnout"),
        "⚠ Socle gratuit réel (création + export PDF), mais options payantes "
        "(modèles avancés, relecture, évaluation de compétences). Tarifs non "
        "établis. Page compte France Travail : "
        "https://cvdesignr.com/fr/compte-france-travail — page NON vérifiée "
        "directement (accès réseau bloqué depuis l'environnement de développement)."),

    # ── Services publics ──────────────────────────────────────────────────
    Ressource(
        "Mes compétences (France Travail)", "https://mescompetences.info",
        "Profil de compétences France Travail. Lien saisi manuellement dans la "
        "fiche de la personne.",
        SERVICE_PUBLIC, ("reconversion", "vae", "handicap", "burnout"),
        "Aucune intégration technique : renvoi manuel uniquement."),
    Ressource(
        "VAE — portail officiel", "https://vae.gouv.fr",
        "Information et dépôt de dossier de validation des acquis de l'expérience.",
        SERVICE_PUBLIC, ("vae", "reconversion", "burnout")),
    Ressource(
        "Cap emploi", "https://capemploi.info",
        "Accompagnement vers l'emploi des personnes en situation de handicap.",
        SERVICE_PUBLIC, ("handicap",)),
    Ressource(
        "Agefiph", "https://agefiph.fr",
        "Aides et dispositifs pour l'emploi des personnes handicapées.",
        SERVICE_PUBLIC, ("handicap",)),
)


# ⚠ MANQUE POUR LE PUBLIC BURN-OUT : aucune ressource spécifique à
# l'épuisement professionnel n'est listée. Les entrées ci-dessus sont des
# outils génériques de reconversion. Le service de prévention et de santé au
# travail, le médecin du travail et les dispositifs de maintien dans l'emploi
# relèvent de ce public — aucune adresse n'est écrite ici faute de l'avoir
# vérifiée. À compléter par Mickael.


def pour_public(cle_public: str) -> list[Ressource]:
    """Ressources proposées pour un public donné (clés de personne.PUBLICS)."""
    return [r for r in RESSOURCES if cle_public in r.publics]
