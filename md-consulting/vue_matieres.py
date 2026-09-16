"""Saisie des résultats scolaires et des affinités.

Un tableau éditable : une ligne par matière. Le croisement moyenne × affinité
est recalculé à l'affichage — il n'est jamais stocké, pour ne pas vieillir.
"""
from __future__ import annotations

import streamlit as st

import matieres as M
import personne as P

# Point de départ quand la fiche est vide. Ce ne sont que des intitulés de
# matières, à corriger : aucune note, aucune affinité pré-remplie.
MATIERES_COURANTES = (
    "Français", "Mathématiques", "Histoire-géographie", "Anglais",
    "Deuxième langue vivante", "Sciences de la vie et de la Terre",
    "Physique-chimie", "EPS",
)

COULEURS = {
    M.APPUI: "🟢", M.A_TRAVAILLER: "🟠", M.SANS_ENVIE: "🔵",
    M.FRAGILITE: "🔴", M.SANS_NOTE: "⚪",
}


def ecran(pers: P.Personne) -> None:
    st.subheader("Résultats scolaires et affinités")
    st.caption(f"Seuil de réussite retenu : {M.SEUIL_REUSSITE:g}/20. "
               "Laissez la moyenne vide si elle n'est pas communiquée : "
               "l'affinité seule reste utile.")

    existantes = M.lister(pers.id)
    if not existantes and st.button("Partir des matières courantes"):
        M.remplacer_tout(pers.id, [M.Matiere(pers.id, nom)
                                   for nom in MATIERES_COURANTES])
        st.rerun()

    lignes = [{"Matière": m.nom,
               "Moyenne /20": m.moyenne,
               "Affinité": m.affinite,
               "Appréciation": m.appreciation or ""}
              for m in existantes]

    edite = st.data_editor(
        lignes, num_rows="dynamic", width="stretch",
        key=f"matieres_{pers.id}",
        column_config={
            "Matière": st.column_config.TextColumn(required=True),
            "Moyenne /20": st.column_config.NumberColumn(
                min_value=0.0, max_value=20.0, step=0.5, format="%.1f"),
            "Affinité": st.column_config.SelectboxColumn(
                options=list(M.AFFINITES), required=True, default=M.NEUTRE),
            "Appréciation": st.column_config.TextColumn(),
        })

    if st.button("Enregistrer les matières", type="primary"):
        retenues = []
        for ligne in edite:
            nom = (ligne.get("Matière") or "").strip()
            if not nom:
                continue
            retenues.append(M.Matiere(
                pers.id, nom, ligne.get("Affinité") or M.NEUTRE,
                moyenne=ligne.get("Moyenne /20"),
                appreciation=(ligne.get("Appréciation") or "").strip() or None))
        try:
            M.remplacer_tout(pers.id, retenues)
        except ValueError as exc:
            st.error(f"Enregistrement bloqué — {exc}")
        else:
            st.rerun()

    if existantes:
        lecture(pers)


def lecture(pers: P.Personne) -> None:
    """Le croisement, rangé par case. C'est là que la séance commence."""
    st.divider()
    generale = M.moyenne_generale(pers.id)
    if generale is not None:
        st.metric("Moyenne des matières renseignées", f"{generale:g}/20")
    groupes = M.par_lecture(pers.id)
    ordre = [M.APPUI, M.A_TRAVAILLER, M.FRAGILITE, M.SANS_ENVIE, M.SANS_NOTE]
    for cle in ordre + [c for c in groupes if c not in ordre]:
        liste = groupes.get(cle)
        if not liste:
            continue
        st.markdown(f"{COULEURS.get(cle, '⚪')} **{cle}** — "
                    + ", ".join(m.nom for m in liste))
