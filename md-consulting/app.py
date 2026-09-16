"""MD Consulting — permanence conseil. Application locale.
Lancement :  streamlit run app.py
Aucune donnée ne sort de cette machine.
"""
from __future__ import annotations

import streamlit as st

import db
import personne as P
import vue_personne

st.set_page_config(page_title="MD Consulting — Conseil", page_icon="🧭", layout="wide")
db.initialiser()

st.title("MD Consulting — Permanence conseil")
st.caption("Données stockées localement (SQLite). Aucun envoi extérieur, aucun export "
           "automatique.")

# ── Barre latérale : filtres et création ───────────────────────────────────
with st.sidebar:
    st.header("Personnes")
    if st.button("➕ Nouvelle fiche", use_container_width=True):
        st.session_state["edition_id"] = None
        st.session_state["mode"] = "creation"
        st.rerun()
    recherche = st.text_input("Rechercher", placeholder="pseudonyme ou nom")
    cles = ["(tous)"] + list(P.PUBLICS)
    filtre = st.selectbox("Public", cles,
                          format_func=lambda k: P.PUBLICS.get(k, "Tous les publics"))

fiches = P.lister(public=None if filtre == "(tous)" else filtre,
                  recherche=recherche.strip() or None)

mode = st.session_state.get("mode")
edition_id = st.session_state.get("edition_id")

# ── Formulaire ─────────────────────────────────────────────────────────────
if mode == "creation":
    vue_personne.formulaire()
    if st.button("Fermer le formulaire"):
        st.session_state["mode"] = None
        st.rerun()
elif edition_id:
    p = P.lire(edition_id)
    if p is None:
        st.session_state["edition_id"] = None
        st.rerun()
    vue_personne.formulaire(p)
    with st.expander("Droit à l'effacement"):
        vue_personne.bloc_suppression(p)
    if st.button("Retour à la liste"):
        st.session_state["edition_id"] = None
        st.rerun()

# ── Liste ──────────────────────────────────────────────────────────────────
else:
    st.subheader(f"{len(fiches)} fiche(s)")
    if not fiches:
        st.info("Aucune fiche. Créez-en une depuis la barre latérale.")
    for p in fiches:
        c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
        c1.markdown(f"**{p.pseudonyme}**" + (f"  \n<small>{p.nom_complet}</small>"
                                             if p.nom_complet else ""),
                    unsafe_allow_html=True)
        c2.write(P.TRANCHES_AGE[p.tranche_age])
        c3.write(P.PUBLICS[p.public])
        if p.consentement_requis:
            if p.consentement_ok:
                c3.caption(f"✅ consentement parental du {p.consentement_parental_date}")
            else:
                c3.caption("⛔ consentement parental manquant")
        if c4.button("Ouvrir", key=f"open_{p.id}", use_container_width=True):
            st.session_state["edition_id"] = p.id
            st.session_state["mode"] = None
            st.rerun()
        st.divider()
