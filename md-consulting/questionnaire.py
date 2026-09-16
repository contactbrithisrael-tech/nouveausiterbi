"""Moteur de questionnaire générique.

Un questionnaire est un fichier JSON déposé dans `questionnaires/`. Le moteur
ne connaît aucun contenu : il lit, valide la forme, affiche et calcule les
totaux par catégorie. Tout le contenu vient des fichiers, jamais du code.

Forme attendue (schéma provisoire, à ajuster quand `investigation_data.js`
sera fourni — voir docs/questionnaires.md) :

    {
      "cle": "motivations_35",
      "titre": "…",
      "consigne": "…",
      "source": "d'où vient ce contenu",
      "echelle": {"min": 1, "max": 5, "libelles": {"1": "…", "5": "…"}},
      "items": [{"id": "m01", "texte": "…", "categorie": "…"}]
    }
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent / "questionnaires"


class QuestionnaireInvalide(ValueError):
    pass


@dataclass(frozen=True)
class Questionnaire:
    cle: str
    titre: str
    items: tuple[dict, ...]
    consigne: str = ""
    source: str = ""
    echelle: dict | None = None

    @property
    def categories(self) -> list[str]:
        vues, ordre = set(), []
        for it in self.items:
            c = it.get("categorie")
            if c and c not in vues:
                vues.add(c); ordre.append(c)
        return ordre


def _valider(brut: dict, origine: str) -> Questionnaire:
    for champ in ("cle", "titre", "items"):
        if champ not in brut:
            raise QuestionnaireInvalide(f"{origine} : champ « {champ} » manquant.")
    items = brut["items"]
    if not isinstance(items, list) or not items:
        raise QuestionnaireInvalide(f"{origine} : « items » doit être une liste non vide.")
    ids = []
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict) or "id" not in it or "texte" not in it:
            raise QuestionnaireInvalide(f"{origine} : item n°{i} sans « id » ou « texte ».")
        ids.append(it["id"])
    if len(set(ids)) != len(ids):
        raise QuestionnaireInvalide(f"{origine} : identifiants d'items en double.")
    ech = brut.get("echelle")
    if ech is not None:
        if not isinstance(ech, dict) or "min" not in ech or "max" not in ech:
            raise QuestionnaireInvalide(f"{origine} : « echelle » doit porter min et max.")
        if ech["min"] >= ech["max"]:
            raise QuestionnaireInvalide(f"{origine} : échelle min ≥ max.")
    return Questionnaire(cle=brut["cle"], titre=brut["titre"], items=tuple(items),
                         consigne=brut.get("consigne", ""), source=brut.get("source", ""),
                         echelle=ech)


def charger(chemin: Path | str) -> Questionnaire:
    chemin = Path(chemin)
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QuestionnaireInvalide(f"{chemin.name} : JSON illisible — {exc}") from exc
    return _valider(brut, chemin.name)


def disponibles(dossier: Path | str | None = None) -> dict[str, Questionnaire]:
    """Questionnaires présents sur le disque. Vide tant qu'aucun n'est fourni."""
    d = Path(dossier or DOSSIER)
    if not d.is_dir():
        return {}
    trouves = {}
    for f in sorted(d.glob("*.json")):
        q = charger(f)
        trouves[q.cle] = q
    return trouves


def totaux_par_categorie(q: Questionnaire, reponses: dict[str, int]) -> dict[str, int]:
    """Somme des réponses par catégorie. Aucune pondération inventée :
    si le contenu prévoit un autre calcul, il devra être décrit dans le fichier."""
    totaux = {c: 0 for c in q.categories}
    for it in q.items:
        cat = it.get("categorie")
        if cat and it["id"] in reponses:
            totaux[cat] += int(reponses[it["id"]])
    return totaux
