"""Écran du compte rendu : quatre blocs, puis export .docx manuel."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import export_docx as X
import personne as P
import rapport as R
import seance as S

AIDES = {
    "bloc_situation": "Assemblé depuis la fiche et l'objectif de la séance.",
    "bloc_tests_utilises": "Assemblé depuis les outils enregistrés.",
    "bloc_resultats": "Assemblé depuis les synthèses des outils passés. "
                      "Les outils non enregistrés (donnée de santé) n'y figurent pas.",
    "bloc_pistes": "Trame vide : nommer un métier à la place du consultant "
                   "serait inventer un conseil depuis des cases cochées.",
    "bloc_competences": "Une ligne par élément, colonnes séparées par « | ». "
                        "Les savoir-être viennent des cases cochées ; les "
                        "savoirs et savoir-faire dépendent du métier visé.",
    "bloc_solutions": "Une ligne par action, colonnes séparées par « | ». "
                      "Les échéances se fixent avec la personne.",
    "bloc_references": "Assemblé depuis les sources des outils passés et les "
                       "ressources du public, avec leur statut d'accès.",
}


def ecran(s: S.Seance, pers: P.Personne) -> None:
    st.subheader("Compte rendu de séance")
    existant = R.lire_par_seance(s.id)
    rap = existant or R.enregistrer(R.preparer(s.id))
    titres = R.intitules(pers.public)

    st.caption("Les quatre blocs sont assemblés depuis la fiche, la séance et "
               "les outils passés. Relisez-les et corrigez : ce sont vos mots "
               "qui sont remis à la personne.")
    if st.button("↻ Tout réassembler depuis la base"):
        R.enregistrer(R.regenerer(rap))
        st.rerun()

    with st.form("rapport"):
        valeurs = {}
        for cle in R.BLOCS:
            entetes = R.BLOCS_TABLEAU.get(cle)
            libelle = titres[cle]
            if entetes:
                libelle += "  —  " + " | ".join(entetes)
            valeurs[cle] = st.text_area(libelle, value=getattr(rap, cle),
                                        height=200 if entetes else 160,
                                        help=AIDES[cle])
        if st.form_submit_button("Enregistrer le compte rendu", type="primary"):
            for cle, v in valeurs.items():
                setattr(rap, cle, v)
            R.enregistrer(rap)
            st.success("Compte rendu enregistré.")
            st.rerun()

    vides = rap.blocs_vides
    if vides:
        st.warning("Blocs encore vides : "
                   + ", ".join(titres[c] for c in vides))

    st.divider()
    st.caption("L'export écrit un fichier sur cette machine. Rien n'est envoyé.")
    if st.button("⬇ Exporter en .docx"):
        chemin = X.exporter(pers, s, rap)
        rap.export_docx_path = str(chemin)
        R.enregistrer(rap)
        st.success(f"Fichier écrit : {chemin}")
        with open(chemin, "rb") as f:
            st.download_button("Télécharger le fichier", f.read(), file_name=chemin.name,
                               mime="application/vnd.openxmlformats-officedocument."
                                    "wordprocessingml.document")
    if rap.export_docx_path and Path(rap.export_docx_path).exists():
        st.caption(f"Dernier export : {rap.export_docx_path}")
