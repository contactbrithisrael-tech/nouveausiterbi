"""Formulaire de fiche Personne (création / modification) et suppression RGPD."""
from __future__ import annotations

from datetime import date

import streamlit as st

import personne as P


def formulaire(existante: P.Personne | None = None) -> None:
    titre = "Modifier la fiche" if existante else "Nouvelle fiche"
    st.subheader(titre)

    p = existante or P.Personne(pseudonyme="", tranche_age="adulte", public="adulte")
    cles_age = list(P.TRANCHES_AGE)
    cles_pub = list(P.PUBLICS)

    with st.form("fiche_personne", clear_on_submit=False):
        c1, c2 = st.columns(2)
        pseudonyme = c1.text_input("Pseudonyme / initiales *", value=p.pseudonyme,
                                   help="Affiché partout dans l'application.")
        nom_complet = c2.text_input("Nom complet (facultatif)", value=p.nom_complet or "",
                                    help="Champ séparé. Jamais utilisé comme identifiant.")

        c3, c4 = st.columns(2)
        tranche = c3.selectbox("Tranche d'âge *", cles_age,
                               index=cles_age.index(p.tranche_age),
                               format_func=lambda k: P.TRANCHES_AGE[k])
        public = c4.selectbox("Public *", cles_pub,
                              index=cles_pub.index(p.public) if p.public in cles_pub else 0,
                              format_func=lambda k: P.PUBLICS[k])

        requis = P.CONSENTEMENT_PARENTAL_REQUIS.get(tranche, False)
        if requis:
            st.warning("Personne mineure : consentement parental obligatoire "
                       "avant tout enregistrement.")
        recueilli = st.checkbox("Consentement parental recueilli",
                                value=bool(p.consentement_parental_date), disabled=not requis)
        date_cons = st.date_input(
            "Date du consentement parental",
            value=date.fromisoformat(p.consentement_parental_date)
            if p.consentement_parental_date else date.today(),
            format="DD/MM/YYYY", disabled=not (requis and recueilli))

        lien = st.text_input("Lien mescompetences.info (saisie manuelle)",
                             value=p.lien_mescompetences or "")
        notes = st.text_area("Notes libres", value=p.notes_libres or "", height=120)

        if st.form_submit_button("Enregistrer", type="primary"):
            p.pseudonyme = pseudonyme
            p.nom_complet = nom_complet.strip() or None
            p.tranche_age = tranche
            p.public = public
            p.consentement_parental_date = (
                date_cons.isoformat() if (requis and recueilli) else None)
            p.lien_mescompetences = lien.strip() or None
            p.notes_libres = notes.strip() or None
            try:
                P.modifier(p) if existante else P.creer(p)
            except (P.ConsentementParentalManquant, P.DonneesInvalides) as exc:
                st.error(f"Enregistrement bloqué — {exc}")
                return
            st.session_state.pop("edition_id", None)
            st.success(f"Fiche « {p.pseudonyme} » enregistrée.")
            st.rerun()


def bloc_suppression(p: P.Personne) -> None:
    """Droit à l'effacement : une confirmation, puis destruction complète."""
    lies = P.compter_liees(p.id)
    st.caption(f"Séances : {lies['seances']} · Tests : {lies['tests']} "
               f"· Rapports : {lies['rapports']}")
    cle = f"confirm_suppr_{p.id}"
    if not st.session_state.get(cle):
        if st.button("Supprimer définitivement", key=f"suppr_{p.id}"):
            st.session_state[cle] = True
            st.rerun()
        return
    st.error("Cette suppression est définitive et efface également les séances, "
             "tests et rapports liés.")
    c1, c2 = st.columns(2)
    if c1.button("Confirmer la suppression", key=f"ok_{p.id}", type="primary"):
        P.supprimer(p.id)
        st.session_state.pop(cle, None)
        st.session_state.pop("edition_id", None)
        st.rerun()
    if c2.button("Annuler", key=f"non_{p.id}"):
        st.session_state.pop(cle, None)
        st.rerun()
