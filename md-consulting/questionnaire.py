"""Moteur de questionnaires.

Le moteur ne contient aucun contenu : chaque questionnaire est un fichier JSON
déposé dans `questionnaires/`, transcrit depuis les documents MD Consulting.
Le code sait afficher et calculer ; il ne sait rien du métier.

Cinq formes, décrites dans docs/questionnaires.md :

    checklist          liste à cocher, avec ou sans définitions
    choix_groupes      questions à choix multiples, rangées par sections
    selection_n        choisir N items dans une liste, puis compter par profil
    likert             affirmations notées sur une échelle, score et thématiques
    ab                 choix forcé entre deux propositions, deux axes
    matrice_360        items croisés avec des évaluateurs, trois niveaux
    questions_ouvertes questions à réponse libre
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent / "questionnaires"

FORMES = ("checklist", "choix_groupes", "selection_n", "likert", "ab",
          "matrice_360", "questions_ouvertes")


class QuestionnaireInvalide(ValueError):
    pass


@dataclass(frozen=True)
class Questionnaire:
    cle: str
    titre: str
    forme: str
    brut: dict = field(repr=False)

    def __getattr__(self, nom):
        try:
            return self.brut[nom]
        except KeyError as exc:
            raise AttributeError(nom) from exc

    def get(self, nom, defaut=None):
        return self.brut.get(nom, defaut)

    @property
    def items(self) -> list[dict]:
        return self.brut.get("items", [])

    @property
    def nb_items(self) -> int:
        if self.forme == "choix_groupes":
            return sum(len(s["questions"]) for s in self.brut["sections"])
        if self.forme == "matrice_360":
            return sum(len(g["items"]) for g in self.brut["groupes"])
        return len(self.items)


# ── Validation ─────────────────────────────────────────────────────────────
def _exige(condition, message):
    if not condition:
        raise QuestionnaireInvalide(message)


def _valider_items(items, origine, champ_texte="texte"):
    _exige(isinstance(items, list) and items, f"{origine} : « items » vide.")
    ids = []
    for i, it in enumerate(items, 1):
        _exige(isinstance(it, dict) and "id" in it and champ_texte in it,
               f"{origine} : item n°{i} sans « id » ou « {champ_texte} ».")
        ids.append(it["id"])
    _exige(len(set(ids)) == len(ids), f"{origine} : identifiants d'items en double.")
    return ids


def valider(brut: dict, origine: str) -> Questionnaire:
    for champ in ("cle", "titre", "forme"):
        _exige(champ in brut, f"{origine} : champ « {champ} » manquant.")
    forme = brut["forme"]
    _exige(forme in FORMES, f"{origine} : forme inconnue « {forme} ».")

    if forme in ("checklist", "selection_n", "likert", "ab", "questions_ouvertes"):
        # le choix forcé porte deux propositions au lieu d'un énoncé
        ids = _valider_items(brut["items"], origine,
                             "a" if forme == "ab" else "texte")

    if forme == "selection_n":
        _exige(isinstance(brut.get("nb_a_selectionner"), int)
               and brut["nb_a_selectionner"] > 0,
               f"{origine} : « nb_a_selectionner » manquant ou nul.")
        profils = brut.get("profils") or {}
        _exige(profils, f"{origine} : « profils » manquant.")
        couverts = [i for p in profils.values() for i in p["items"]]
        _exige(sorted(couverts) == sorted(ids),
               f"{origine} : la grille de profils ne couvre pas exactement les items "
               f"({len(couverts)} entrées pour {len(ids)} items).")

    if forme == "likert":
        ech = brut.get("echelle")
        _exige(isinstance(ech, list) and len(ech) >= 2,
               f"{origine} : « echelle » doit lister au moins deux niveaux.")
        for niveau in ech:
            _exige("libelle" in niveau and "points" in niveau,
                   f"{origine} : un niveau d'échelle sans « libelle » ou « points ».")

    if forme == "ab":
        for it in brut["items"]:
            _exige("b" in it, f"{origine} : item {it['id']} sans proposition « b ».")
        _exige(brut.get("axes"), f"{origine} : « axes » manquant.")
        cotes = [i for axe in brut["axes"] for i in axe["cle"]]
        _exige(sorted(cotes) == sorted(ids),
               f"{origine} : la clé de cotation ne couvre pas exactement les items "
               f"({len(cotes)} entrées pour {len(ids)} items).")

    if forme == "choix_groupes":
        _exige(brut.get("sections"), f"{origine} : « sections » manquant.")
        vus = []
        for s in brut["sections"]:
            _exige("titre" in s and s.get("questions"),
                   f"{origine} : section sans titre ou sans questions.")
            for q in s["questions"]:
                _exige({"id", "texte", "choix"} <= set(q),
                       f"{origine} : question incomplète dans « {s['titre']} ».")
                vus.append(q["id"])
        _exige(len(set(vus)) == len(vus), f"{origine} : identifiants de questions en double.")

    if forme == "matrice_360":
        _exige(brut.get("evaluateurs"), f"{origine} : « evaluateurs » manquant.")
        _exige(brut.get("niveaux"), f"{origine} : « niveaux » manquant.")
        _exige(brut.get("groupes"), f"{origine} : « groupes » manquant.")
        for g in brut["groupes"]:
            _valider_items(g["items"], f"{origine}/{g.get('titre', '?')}")

    return Questionnaire(cle=brut["cle"], titre=brut["titre"], forme=forme, brut=brut)


# ── Chargement ─────────────────────────────────────────────────────────────
def charger(chemin: Path | str) -> Questionnaire:
    chemin = Path(chemin)
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QuestionnaireInvalide(f"{chemin.name} : JSON illisible — {exc}") from exc
    return valider(brut, chemin.name)


def disponibles(dossier: Path | str | None = None) -> dict[str, Questionnaire]:
    d = Path(dossier or DOSSIER)
    if not d.is_dir():
        return {}
    trouves = {}
    for f in sorted(d.glob("*.json")):
        q = charger(f)
        trouves[q.cle] = q
    return trouves


# ── Calculs ────────────────────────────────────────────────────────────────
def profils_par_selection(q: Questionnaire, choisis: list[str]) -> list[tuple[str, int]]:
    """Grille de profils : combien d'items retenus tombent dans chaque profil.
    Classement décroissant. Aucune pondération : le document n'en prévoit pas."""
    retenus = set(choisis)
    comptes = [(nom, len(retenus & set(p["items"])))
               for nom, p in q.profils.items()]
    return sorted(comptes, key=lambda c: (-c[1], c[0]))


def score_likert(q: Questionnaire, reponses: dict[str, str]) -> dict:
    """Score total et moyenne par thématique. Les thématiques ne sont calculées
    que si le document précise quels items s'y rattachent."""
    points = {n["libelle"]: n["points"] for n in q.echelle}
    total = sum(points.get(v, 0) for v in reponses.values())
    maxi = len(q.items) * max(points.values())
    resultat = {"total": total, "maximum": maxi, "thematiques": {}}
    for t in q.get("thematiques", []):
        lies = t.get("items") or []
        if not lies:
            continue
        notes = [points.get(reponses[i], 0) for i in lies if i in reponses]
        if notes:
            resultat["thematiques"][t["nom"]] = round(sum(notes) / len(notes), 2)
    for tranche in q.get("interpretation", []):
        if tranche["min"] <= total <= tranche["max"]:
            resultat["lecture"] = tranche["texte"]
            break
    return resultat


def score_ab(q: Questionnaire, reponses: dict[str, str]) -> dict:
    """Choix forcé : un point par réponse conforme à la clé, axe par axe."""
    scores = {axe["nom"]: 0 for axe in q.axes}
    for axe in q.axes:
        for item_id, attendu in axe["cle"].items():
            if reponses.get(item_id) == attendu:
                scores[axe["nom"]] += 1
    return scores
