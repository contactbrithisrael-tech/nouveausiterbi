"""RésultatTest : réponses brutes et synthèse, rattachées à une séance."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import db
import questionnaire as Q

# Tests passés à l'extérieur : on ne stocke qu'une synthèse saisie à la main
TYPES_EXTERNES = {
    "riasec_externe": "RIASEC (test externe)",
    "big_five_externe": "Big Five / IPIP (test externe)",
    "assessfirst_externe": "AssessFirst (test externe)",
}


def types_investigation() -> dict[str, str]:
    """Outils d'investigation réellement installés dans questionnaires/.
    La liste vient des fichiers, jamais d'une liste figée dans le code."""
    return {cle: q.titre for cle, q in Q.disponibles().items()}


def types() -> dict[str, str]:
    return {**types_investigation(), **TYPES_EXTERNES}


def libelle(cle: str) -> str:
    return types().get(cle, cle)


@dataclass
class ResultatTest:
    seance_id: str
    type_test: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reponses: dict | list | None = None
    synthese_texte: str | None = None
    date_saisie: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def valider(self) -> None:
        if self.type_test not in types():
            raise ValueError(
                f"Type de test inconnu : {self.type_test!r}. Les outils "
                "d'investigation sont les fichiers présents dans questionnaires/.")
        if not self.seance_id:
            raise ValueError("Un résultat doit être rattaché à une séance.")
        if self.type_test in TYPES_EXTERNES and not (self.synthese_texte or "").strip():
            raise ValueError(
                "Un test passé à l'extérieur n'est enregistré qu'avec sa synthèse : "
                "l'outil ne recopie pas les résultats bruts d'un tiers.")


def creer(r: ResultatTest, chemin: Path | str | None = None) -> ResultatTest:
    r.valider()
    with db.connexion(chemin) as cx:
        if not cx.execute("SELECT 1 FROM seance WHERE id = ?", (r.seance_id,)).fetchone():
            raise ValueError("Séance introuvable : résultat non enregistré.")
        cx.execute(
            "INSERT INTO resultat_test (id, seance_id, type_test, reponses_json, "
            "synthese_texte, date_saisie) VALUES (?,?,?,?,?,?)",
            (r.id, r.seance_id, r.type_test,
             json.dumps(r.reponses, ensure_ascii=False) if r.reponses is not None else None,
             r.synthese_texte, r.date_saisie))
    return r


def _depuis_ligne(l) -> ResultatTest:
    return ResultatTest(
        id=l["id"], seance_id=l["seance_id"], type_test=l["type_test"],
        reponses=json.loads(l["reponses_json"]) if l["reponses_json"] else None,
        synthese_texte=l["synthese_texte"], date_saisie=l["date_saisie"])


def lister_par_seance(seance_id: str, chemin: Path | str | None = None) -> list[ResultatTest]:
    with db.connexion(chemin) as cx:
        return [_depuis_ligne(l) for l in cx.execute(
            "SELECT * FROM resultat_test WHERE seance_id = ? ORDER BY date_saisie",
            (seance_id,))]


def enregistrer_synthese(resultat_id: str, texte: str,
                         chemin: Path | str | None = None) -> None:
    with db.connexion(chemin) as cx:
        cx.execute("UPDATE resultat_test SET synthese_texte = ? WHERE id = ?",
                   (texte, resultat_id))


def supprimer(resultat_id: str, chemin: Path | str | None = None) -> bool:
    with db.connexion(chemin) as cx:
        c = cx.execute("DELETE FROM resultat_test WHERE id = ?", (resultat_id,))
    return c.rowcount > 0
