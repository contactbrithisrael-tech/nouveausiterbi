"""Écran des ressources externes, classées par public."""
from __future__ import annotations

import streamlit as st

import personne as P
import ressources as Rs

COULEURS = {Rs.LIBRE: "🟢", Rs.SERVICE_PUBLIC: "🔵",
            Rs.COMPTE_REQUIS: "🟠", Rs.FREEMIUM: "🟠"}


def ecran(public_defaut: str | None = None) -> None:
    st.subheader("Ressources externes")
    st.caption("Aucune donnée n'est transmise à ces services par l'outil : "
               "ce sont des liens à remettre à la personne.")
    cles = list(P.PUBLICS)
    index = cles.index(public_defaut) if public_defaut in cles else 0
    public = st.selectbox("Public", cles, index=index,
                          format_func=lambda k: P.PUBLICS[k])

    garde = Rs.MISES_EN_GARDE.get(public)
    if garde:
        st.warning(garde)

    liste = Rs.pour_public(public)
    if not liste:
        st.info("Aucune ressource pour ce public.")
        return
    for r in liste:
        st.markdown(f"{COULEURS.get(r.acces, '⚪')} **[{r.nom}]({r.url})** "
                    f"— *{r.acces}*")
        st.caption(r.description)
        if r.note:
            st.caption(f"⚠ {r.note}")
        st.divider()
