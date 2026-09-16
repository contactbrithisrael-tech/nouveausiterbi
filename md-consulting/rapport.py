"""Rapport en quatre blocs, identiques pour tous les publics.
Seuls les intitulés et les pistes proposées changent selon le public.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import dates_fr
import db
import matieres as M
import personne as P
import questionnaire as Q
import ressources as Rs
import resultat_test as RT
import seance as S

# Sept blocs, dans l'ordre, reprenant la trame d'une synthèse de bilan de
# compétences sans en emprunter l'identité réglementaire : ni visa des
# articles R6313-4 et suivants, ni numéro de certification (voir config.py).
BLOCS = ("bloc_situation", "bloc_tests_utilises", "bloc_scolaire",
         "bloc_resultats", "bloc_pistes", "bloc_competences", "bloc_solutions",
         "bloc_references")

# Certains blocs ne concernent qu'une partie des publics : un adulte en
# reconversion n'a pas de bulletin, un collégien n'a pas de Parcoursup.
PUBLICS_DU_BLOC = {"bloc_scolaire": ("college", "lycee")}

# Blocs rendus sous forme de tableau à l'export, une ligne par « | ».
BLOCS_TABLEAU = {
    "bloc_scolaire": ("Matière", "Moyenne", "Affinité", "Lecture"),
    "bloc_competences": ("Domaine", "Élément", "Niveau"),
    "bloc_solutions": ("Échéance", "Action à réaliser", "Moyens nécessaires"),
}

INTITULES_COMMUNS = {
    "bloc_situation": "Situation et demande",
    "bloc_tests_utilises": "Déroulé de la séance et outils utilisés",
    "bloc_resultats": "Ce qui ressort",
    "bloc_scolaire": "Résultats scolaires et affinités",
    "bloc_competences": "Points d'appui et éléments à développer",
    "bloc_references": "Références et ressources pour affiner",
}

# Le bloc « pistes » porte le vocabulaire du public reçu.
INTITULES_PISTES = {
    "college": "Pistes évoquées",
    "lycee": "Pistes d'orientation envisagées",
    "reconversion": "Pistes professionnelles envisagées",
    "vae": "Certification et pistes envisagées",
    "handicap": "Pistes envisagées et appuis",
    "burnout": "Pistes évoquées, sans engagement de calendrier",
}

INTITULES_SOLUTIONS = {
    "college": "Plan d'action",
    "lycee": "Plan d'action",
    "reconversion": "Plan d'action",
    "vae": "Plan d'action — démarches VAE",
    "handicap": "Plan d'action",
    "burnout": "Plan d'action, à rythme tenable",
}


def blocs_pour(public: str) -> tuple[str, ...]:
    """Les blocs qui concernent ce public, dans l'ordre."""
    return tuple(b for b in BLOCS
                 if public in PUBLICS_DU_BLOC.get(b, (public,)))


def intitules(public: str) -> dict[str, str]:
    return {**INTITULES_COMMUNS,
            "bloc_pistes": INTITULES_PISTES.get(public, "Pistes envisagées"),
            "bloc_solutions": INTITULES_SOLUTIONS.get(public, "Plan d'action")}


@dataclass
class Rapport:
    seance_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date_generation: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    bloc_situation: str = ""
    bloc_tests_utilises: str = ""
    bloc_scolaire: str = ""
    bloc_resultats: str = ""
    bloc_pistes: str = ""
    bloc_competences: str = ""
    bloc_solutions: str = ""
    bloc_references: str = ""
    export_docx_path: str | None = None

    @property
    def blocs_vides(self) -> list[str]:
        return [b for b in BLOCS if not getattr(self, b).strip()]

    def valider(self) -> None:
        if not self.seance_id:
            raise ValueError("Un rapport doit être rattaché à une séance.")


def resume_tests(seance_id: str, chemin: Path | str | None = None) -> str:
    """Bloc « outils utilisés » : liste factuelle, rédigée depuis la base.
    C'est le seul bloc que l'outil remplit seul — les trois autres relèvent
    du consultant, pas d'une génération automatique."""
    resultats = RT.lister_par_seance(seance_id, chemin)
    if not resultats:
        return "Aucun outil enregistré pour cette séance."
    lignes = []
    for r in resultats:
        lignes.append(f"{RT.libelle(r.type_test)} — "
                      f"{dates_fr.jour(r.date_saisie)}")
    return "\n".join(lignes)


def composer_situation(pers: P.Personne, sea: S.Seance) -> str:
    """Bloc 1, assemblé depuis la fiche et la séance. Que des faits saisis."""
    lignes = [f"Personne reçue : {pers.nom_affiche}"
              + (f", {pers.age} ans" if pers.age is not None else "")
              + f" — {P.PUBLICS[pers.public]}."]
    if pers.rqth:
        lignes.append("Reconnaissance de la qualité de travailleur handicapé (RQTH).")
    if pers.situation:
        lignes.append(f"Situation : {pers.situation}.")
    lignes.append(f"Séance du {dates_fr.jour(sea.date)}, "
                  f"durée prévue {sea.chrono_max_minutes} minutes.")
    if sea.objectif_texte:
        lignes.append(f"Objectif annoncé : {sea.objectif_texte}")
    if pers.notes_libres:
        lignes.append(f"Notes de séance : {pers.notes_libres}")
    return "\n".join(lignes)


def composer_resultats(seance_id: str, chemin: Path | str | None = None) -> str:
    """Bloc 3 : les synthèses des outils passés, mises bout à bout.

    Aucune interprétation ajoutée : ce qui apparaît ici a été produit par les
    grilles des outils eux-mêmes. Les outils marqués « donnée de santé » n'y
    figurent pas — rien n'en a été enregistré, il n'y a rien à reprendre.
    """
    resultats = RT.lister_par_seance(seance_id, chemin)
    if not resultats:
        return ""
    blocs = []
    for r in resultats:
        if not (r.synthese_texte or "").strip():
            continue
        blocs.append(f"{RT.libelle(r.type_test)}\n{r.synthese_texte.strip()}")
    return "\n\n".join(blocs)


def composer_pistes(pers: P.Personne) -> str:
    """Bloc 4 : la trame du bilan, vide.

    Les trois questions viennent de la synthèse de référence : pistes
    explorées, écartées et pourquoi, retenues. Nommer un métier à la place du
    consultant serait inventer un conseil à partir de cases cochées : les
    lignes restent à remplir.
    """
    return "\n".join([
        "Pistes explorées pendant la séance :",
        "- ",
        "",
        "Pistes écartées, et pourquoi :",
        "- ",
        "",
        f"{'Piste retenue' if pers.public != 'college' else 'Direction retenue'} "
        "à ce stade :",
        "- ",
    ])


NIVEAUX_COMPETENCES = ("acquis", "à renforcer", "à développer")
DOMAINES_COMPETENCES = ("Savoirs", "Savoir-faire", "Savoir-être")


def composer_competences(seance_id: str, chemin: Path | str | None = None) -> str:
    """Bloc 5 : tableau « domaine | élément | niveau ».

    Les savoir-être remontent des cases réellement cochées : ce que la
    personne a retenu dans « Points forts » est acquis, ce qu'elle a retenu
    dans « Points de vigilance » est à développer. Les savoirs et
    savoir-faire dépendent du métier visé : leurs lignes restent vides.
    """
    lignes = []
    installes = Q.disponibles()
    for r in RT.lister_par_seance(seance_id, chemin):
        q = installes.get(r.type_test)
        coches = (r.reponses or {}).get("coches") if isinstance(r.reponses, dict) else None
        if not q or not coches:
            continue
        niveau = {"points_forts": "acquis",
                  "points_vigilance": "à développer"}.get(r.type_test)
        if not niveau:
            continue
        for it in q.items:
            if it["id"] in coches:
                lignes.append(f"Savoir-être | {it['texte']} | {niveau}")
    for domaine in ("Savoirs", "Savoir-faire"):
        lignes.append(f"{domaine} |  | ")
    return "\n".join(lignes)


def composer_scolaire(pers: P.Personne, chemin: Path | str | None = None) -> str:
    """Bloc scolaire : tableau « matière | moyenne | affinité | lecture ».

    La lecture est le croisement de la note et de l'affinité, calculé par
    matieres.py. Le seuil de réussite est rappelé, parce que c'est une
    convention et qu'elle doit pouvoir être discutée.
    """
    liste = M.lister(pers.id, chemin)
    if not liste:
        return ""
    lignes = [f"Seuil de réussite retenu : {M.SEUIL_REUSSITE:g}/20."]
    generale = M.moyenne_generale(pers.id, chemin)
    if generale is not None:
        lignes[0] += f" Moyenne générale des matières renseignées : {generale:g}/20."
    for m in liste:
        moyenne = f"{m.moyenne:g}/20" if m.moyenne is not None else "—"
        lignes.append(f"{m.nom} | {moyenne} | {m.affinite} | {m.lecture}")
    return "\n".join(lignes)


# Étapes de la procédure Parcoursup, au mois près. Les dates exactes changent
# à chaque campagne : elles ne sont pas écrites en dur, la page officielle
# reste la seule référence.
ETAPES_PARCOURSUP = (
    ("Décembre à janvier", "S'informer sur les formations et leurs attendus",
     "parcoursup.gouv.fr, onisep.fr"),
    ("Janvier à mars", "S'inscrire et formuler ses vœux", "Parcoursup"),
    ("Avant début avril", "Confirmer les vœux et finaliser le dossier",
     "Parcoursup"),
    ("À partir de début juin", "Recevoir les réponses et répondre aux "
     "propositions d'admission", "Parcoursup"),
    ("Juin à septembre", "Phase complémentaire, si besoin", "Parcoursup"),
)


def composer_plan_action(pers: P.Personne, seance_id: str,
                         chemin: Path | str | None = None) -> str:
    """Bloc 6 : tableau « échéance | action | moyens ».

    Les actions sont celles que les outils passés prévoient eux-mêmes après
    la passation ; les échéances restent vides, elles se fixent avec la
    personne et non depuis une base de données. Les lignes libres sont là
    pour les démarches décidées en séance.
    """
    lignes = []
    if pers.public == "lycee":
        lignes.append("Calendrier Parcoursup : les dates exactes changent à "
                      "chaque campagne, à vérifier sur "
                      "parcoursup.gouv.fr/calendrier.")
    installes = Q.disponibles()
    passes = list(dict.fromkeys(r.type_test for r in
                                RT.lister_par_seance(seance_id, chemin)))
    for cle in passes:
        q = installes.get(cle)
        for etape in (q.get("suite", []) if q else []):
            lignes.append(f" | {etape} | {q.titre}")
    if pers.public == "lycee":
        for echeance, action, moyens in ETAPES_PARCOURSUP:
            lignes.append(f"{echeance} | {action} | {moyens}")
    # Les ressources ne sont pas transformées en actions : prescrire « prendre
    # connaissance de X » à tout le monde serait inventer une démarche. Elles
    # figurent dans les références, où la personne va les chercher si besoin.
    lignes += [" |  | "] * 4
    return "\n".join(lignes)


def composer_references(pers: P.Personne, seance_id: str,
                        chemin: Path | str | None = None) -> str:
    """Bloc 7 : d'où viennent les outils, et où aller pour approfondir.

    Chaque outil passé cite sa source — c'est un champ obligatoire à l'usage
    des fichiers de questionnaires. S'y ajoutent les ressources du public
    avec leur statut d'accès, pour que personne ne découvre un paiement en
    cliquant.
    """
    lignes = []
    installes = Q.disponibles()
    passes = list(dict.fromkeys(r.type_test for r in
                                RT.lister_par_seance(seance_id, chemin)))
    sources = []
    for cle in passes:
        q = installes.get(cle)
        if q and q.get("source"):
            sources.append(f"- {q.titre} : {q.source}")
    if sources:
        lignes.append("Outils utilisés pendant la séance :")
        lignes += sources
        lignes.append("")
    ressources = Rs.pour_public(pers.public)
    if ressources:
        lignes.append("Ressources à consulter pour approfondir :")
        for r in ressources:
            lignes.append(f"- {r.nom} ({r.acces}) — {r.url}")
            lignes.append(f"  {r.description}")
    orientation = Rs.ORIENTATIONS_BENEFICIAIRE.get(pers.public)
    if orientation:
        lignes += ["", orientation]
    return "\n".join(lignes)


def composer(pers: P.Personne, sea: S.Seance,
             chemin: Path | str | None = None) -> dict[str, str]:
    """Les quatre blocs, assemblés depuis la base. Tous modifiables ensuite."""
    return {
        "bloc_situation": composer_situation(pers, sea),
        "bloc_tests_utilises": resume_tests(sea.id, chemin),
        "bloc_scolaire": composer_scolaire(pers, chemin),
        "bloc_resultats": composer_resultats(sea.id, chemin),
        "bloc_pistes": composer_pistes(pers),
        "bloc_competences": composer_competences(sea.id, chemin),
        "bloc_solutions": composer_plan_action(pers, sea.id, chemin),
        "bloc_references": composer_references(pers, sea.id, chemin),
    }


def preparer(seance_id: str, chemin: Path | str | None = None) -> Rapport:
    """Compte rendu assemblé automatiquement, prêt à être relu et corrigé."""
    sea = S.lire(seance_id, chemin)
    if sea is None:
        raise ValueError("Séance introuvable.")
    pers = P.lire(sea.personne_id, chemin)
    if pers is None:
        raise ValueError("Personne introuvable.")
    return Rapport(seance_id=seance_id, **composer(pers, sea, chemin))


def regenerer(rap: Rapport, chemin: Path | str | None = None) -> Rapport:
    """Réécrit les quatre blocs depuis la base, en écrasant les retouches."""
    sea = S.lire(rap.seance_id, chemin)
    pers = P.lire(sea.personne_id, chemin)
    for cle, texte in composer(pers, sea, chemin).items():
        setattr(rap, cle, texte)
    return rap


_COLONNES = ("id, seance_id, date_generation, bloc_situation, bloc_tests_utilises, "
             "bloc_scolaire, bloc_resultats, bloc_pistes, bloc_competences, "
             "bloc_solutions, bloc_references, export_docx_path")


def enregistrer(r: Rapport, chemin: Path | str | None = None) -> Rapport:
    """Insère ou remplace. Un seul compte rendu par séance : la contrainte
    d'unicité fait que le précédent est écarté, quel que soit son identifiant."""
    r.valider()
    with db.connexion(chemin) as cx:
        if not cx.execute("SELECT 1 FROM seance WHERE id = ?", (r.seance_id,)).fetchone():
            raise ValueError("Séance introuvable : rapport non enregistré.")
        cx.execute(f"INSERT OR REPLACE INTO rapport ({_COLONNES}) "
                   "VALUES (" + ",".join("?" * (len(BLOCS) + 4)) + ")",
                   (r.id, r.seance_id, r.date_generation)
                   + tuple(getattr(r, b) for b in BLOCS)
                   + (r.export_docx_path,))
    return r


def lire_par_seance(seance_id: str, chemin: Path | str | None = None) -> Rapport | None:
    with db.connexion(chemin) as cx:
        l = cx.execute(f"SELECT {_COLONNES} FROM rapport WHERE seance_id = ?",
                       (seance_id,)).fetchone()
    if not l:
        return None
    return Rapport(id=l["id"], seance_id=l["seance_id"],
                   date_generation=l["date_generation"],
                   export_docx_path=l["export_docx_path"],
                   **{b: l[b] or "" for b in BLOCS})
