"""MD Consulting — permanence conseil. Application locale.
Lancement :  streamlit run app.py
Aucune donnée ne sort de cette machine.
"""
from __future__ import annotations

import streamlit as st

import config
import db
import personne as P
import seance as S
import vue_personne
import vue_rapport
import vue_ressources
import vue_seance

st.set_page_config(page_title="MD Consulting — Conseil", page_icon="🧭", layout="wide")
db.initialiser()


def aller(**etat) -> None:
    st.session_state.update(etat)
    st.rerun()


st.title(config.ORGANISATION["nom"] + " — Permanence conseil")
st.caption("Données stockées localement (SQLite). Aucun envoi extérieur, "
           "aucun export automatique.")

with st.sidebar:
    page = st.radio("Écran", ["Personnes", "Ressources"], label_visibility="collapsed")
    if page == "Personnes":
        st.header("Personnes")
        if st.button("➕ Nouvelle fiche", use_container_width=True):
            aller(page_personne="creation", personne_id=None, seance_id=None)
        recherche = st.text_input("Rechercher", placeholder="pseudonyme ou nom")
        cles = ["(tous)"] + list(P.PUBLICS)
        filtre = st.selectbox("Public", cles,
                              format_func=lambda k: P.PUBLICS.get(k, "Tous les publics"))

if page == "Ressources":
    pers = P.lire(st.session_state.get("personne_id") or "")
    vue_ressources.ecran(pers.public if pers else None)
    st.stop()

# ── Écran séance ───────────────────────────────────────────────────────────
seance_id = st.session_state.get("seance_id")
if seance_id:
    s = S.lire(seance_id)
    if s is None:
        aller(seance_id=None)
    pers = P.lire(s.personne_id)
    if st.button("← Retour à la fiche"):
        aller(seance_id=None, personne_id=s.personne_id)
    vue_seance.entete_seance(s, pers)
    st.divider()
    vue_seance.outils(s)
    st.divider()
    vue_rapport.ecran(s, pers)
    st.stop()

# ── Écran fiche ────────────────────────────────────────────────────────────
if st.session_state.get("page_personne") == "creation":
    vue_personne.formulaire()
    if st.button("Fermer le formulaire"):
        aller(page_personne=None)
    st.stop()

personne_id = st.session_state.get("personne_id")
if personne_id:
    pers = P.lire(personne_id)
    if pers is None:
        aller(personne_id=None)
    if st.button("← Retour à la liste"):
        aller(personne_id=None)
    onglet_fiche, onglet_seances = st.tabs(["Fiche", "Séances"])
    with onglet_fiche:
        vue_personne.formulaire(pers)
        with st.expander("Droit à l'effacement"):
            vue_personne.bloc_suppression(pers)
    with onglet_seances:
        vue_seance.liste_seances(pers)
    st.stop()

# ── Liste des personnes ────────────────────────────────────────────────────
fiches = P.lister(public=None if filtre == "(tous)" else filtre,
                  recherche=recherche.strip() or None)
st.subheader(f"{len(fiches)} fiche(s)")
if not fiches:
    st.info("Aucune fiche. Créez-en une depuis la barre latérale.")
for p in fiches:
    c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
    c1.markdown(f"**{p.pseudonyme}**"
                + (f"  \n<small>{p.nom_complet}</small>" if p.nom_complet else ""),
                unsafe_allow_html=True)
    c2.write(P.TRANCHES_AGE[p.tranche_age])
    c3.write(P.PUBLICS[p.public])
    if p.consentement_requis:
        c3.caption(f"✅ consentement parental du {p.consentement_parental_date}"
                   if p.consentement_ok else "⛔ consentement parental manquant")
    if c4.button("Ouvrir", key=f"open_{p.id}", use_container_width=True):
        aller(personne_id=p.id, page_personne=None, seance_id=None)
    st.divider()
