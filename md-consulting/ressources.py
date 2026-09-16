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


# Avertissement affiché avant la liste, pour les publics où un lien mal
# employé fait plus de mal que de bien.
MISES_EN_GARDE = {
    "burnout": (
        "**L'épuisement professionnel relève de la santé au travail** : médecin "
        "du travail, médecin traitant, psychologue. Dans les classifications "
        "médicales internationales, le burn-out n'est pas une maladie mais un "
        "phénomène lié au travail — aucun questionnaire ne le diagnostique. "
        "Le CBI figure parmi les outils à la demande expresse du consultant : "
        "c'est une échelle de mesure sans seuil individuel, son résultat "
        "s'affiche en séance et **n'est jamais enregistré**. Une moyenne élevée "
        "n'est pas un diagnostic et n'exonère pas d'orienter."
    ),
}


# Texte destiné à la PERSONNE REÇUE, repris dans le compte rendu qu'elle
# emporte. À distinguer de MISES_EN_GARDE, qui s'adresse au consultant et
# n'a rien à faire dans un document remis.
ORIENTATIONS_BENEFICIAIRE = {
    "burnout": (
        "L'épuisement professionnel relève de la santé au travail. Les "
        "interlocuteurs sont le médecin du travail, le médecin traitant et le "
        "psychologue. Le dispositif « Mon soutien psy » de l'Assurance Maladie "
        "permet de consulter un psychologue sans prescription préalable. "
        "Ce compte rendu restitue une séance de conseil : il ne constitue pas "
        "un avis médical."
    ),
    "handicap": (
        "Cap emploi et l'Agefiph accompagnent l'accès et le maintien dans "
        "l'emploi des personnes en situation de handicap."
    ),
}


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
    # ── Épuisement professionnel ───────────────────────────────────────────
    Ressource(
        "INRS — Épuisement professionnel (burnout)",
        "https://www.inrs.fr/risques/epuisement-burnout/ce-qu-il-faut-retenir.html",
        "Référence française sur le syndrome d'épuisement professionnel : "
        "définition, facteurs de risque, cadre de prévention. Institut national "
        "de recherche et de sécurité.",
        SERVICE_PUBLIC, ("burnout", "handicap", "reconversion"),
        "L'INRS rappelle que le burn-out n'est pas classé comme une maladie "
        "dans les classifications médicales internationales, mais parmi les "
        "problèmes liés au travail. Il n'y a donc rien à « dépister » ici."),
    Ressource(
        "Mon soutien psy (Assurance Maladie)",
        "https://www.ameli.fr/assure/remboursements/rembourse/"
        "remboursement-seance-psychologue-mon-soutien-psy",
        "Séances chez un psychologue partiellement remboursées, sans "
        "prescription médicale préalable. Annuaire des psychologues "
        "partenaires sur ameli.fr.",
        SERVICE_PUBLIC, ("burnout", "handicap", "reconversion", "lycee"),
        "La voie la plus directe à indiquer à une personne en souffrance "
        "psychique : elle prend rendez-vous elle-même. Conditions et nombre de "
        "séances à vérifier sur ameli.fr, ils évoluent."),
    Ressource(
        "Cap emploi", "https://capemploi.info",
        "Accompagnement vers l'emploi des personnes en situation de handicap.",
        SERVICE_PUBLIC, ("handicap",)),
    Ressource(
        "Agefiph", "https://agefiph.fr",
        "Aides et dispositifs pour l'emploi des personnes handicapées.",
        SERVICE_PUBLIC, ("handicap",)),
)


# ── Sur les instruments de mesure du burn-out ──────────────────────────────
# Le CBI est intégré depuis que Mickael Darmon l'a demandé après avoir lu les
# réserves ci-dessous, et il en assume l'usage. Il est marqué comme donnée de
# santé : son résultat ne quitte pas l'écran de séance.
#
# L'état des lieux vérifié :
#   · MBI (Maslach Burnout Inventory) — instrument de référence, sous licence
#     payante exclusive (Mind Garden), facturé à l'administration. Le
#     reproduire ici serait une contrefaçon, et la règle du projet exclut déjà
#     les instruments payants.
#   · CBI (Copenhagen Burnout Inventory) — domaine public, 19 items, trois
#     sous-échelles (épuisement personnel, lié au travail, lié aux usagers).
#     Publication d'origine : Kristensen, Borritz, Villadsen & Christensen,
#     « The Copenhagen Burnout Inventory », Work & Stress, 2005. Aucune
#     adresse de diffusion n'est écrite ici : celles trouvées n'ont pas pu
#     être vérifiées depuis l'environnement de développement. À récupérer
#     depuis la publication d'origine.
#   · Aucun de ces instruments ne pose de diagnostic individuel. Ce sont des
#     échelles de mesure, conçues pour la recherche et l'épidémiologie.


def pour_public(cle_public: str) -> list[Ressource]:
    """Ressources proposées pour un public donné (clés de personne.PUBLICS)."""
    return [r for r in RESSOURCES if cle_public in r.publics]
