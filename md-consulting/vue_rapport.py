"""Écran du compte rendu : quatre blocs, puis export .docx manuel."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import export_docx as X
import personne as P
import rapport as R
import seance as S

AIDES = {
    "bloc_situation": "Pourquoi la personne est venue, d'où elle part.",
    "bloc_tests_utilises": "Pré-rempli depuis les outils enregistrés. Modifiable.",
    "bloc_resultats": "Synthèse qualitative. Jamais des scores bruts seuls.",
    "bloc_solutions": "Pistes concrètes et prochaines démarches, datées si possible.",
}


def ecran(s: S.Seance, pers: P.Personne) -> None:
    st.subheader("Compte rendu de séance")
    rap = R.lire_par_seance(s.id) or R.preparer(s.id)
    titres = R.intitules(pers.public)

    if st.button("↻ Recalculer le bloc « outils utilisés »"):
        rap.bloc_tests_utilises = R.resume_tests(s.id)
        R.enregistrer(rap)
        st.rerun()

    with st.form("rapport"):
        valeurs = {}
        for cle in R.BLOCS:
            valeurs[cle] = st.text_area(titres[cle], value=getattr(rap, cle),
                                        height=160, help=AIDES[cle])
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
