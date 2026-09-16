"""Fiche de renseignement : formulaire complet et suppression RGPD."""
from __future__ import annotations

from datetime import date

import streamlit as st

import dates_fr
import personne as P

NAISSANCE_MIN = date(1930, 1, 1)


def _date_ou(valeur: str | None, defaut: date) -> date:
    try:
        return date.fromisoformat(valeur) if valeur else defaut
    except ValueError:
        return defaut


def formulaire(existante: P.Personne | None = None) -> None:
    st.subheader("Modifier la fiche" if existante else "Nouvelle fiche")

    p = existante or P.Personne(nom="", prenom="", tranche_age="adulte", public="adulte")
    cles_age, cles_pub = list(P.TRANCHES_AGE), list(P.PUBLICS)

    with st.form("fiche_personne"):
        st.markdown("**Identité**")
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nom *", value=p.nom)
        prenom = c2.text_input("Prénom *", value=p.prenom)

        c3, c4 = st.columns(2)
        naissance_connue = c3.checkbox("Date de naissance connue",
                                       value=bool(p.date_naissance))
        naissance = c4.date_input(
            "Date de naissance", value=_date_ou(p.date_naissance, date(2000, 1, 1)),
            min_value=NAISSANCE_MIN, max_value=date.today(), format="DD/MM/YYYY",
            disabled=not naissance_connue)
        date_naissance = naissance.isoformat() if naissance_connue else None

        age = P.age_au(date_naissance)
        if age is not None:
            st.caption(f"Âge : **{age} ans** — tranche déduite : "
                       f"{P.TRANCHES_AGE[P.tranche_pour_age(age)]}")

        c5, c6 = st.columns(2)
        tranche = c5.selectbox("Tranche d'âge *", cles_age,
                               index=cles_age.index(
                                   P.tranche_pour_age(age) if age is not None
                                   else p.tranche_age),
                               format_func=lambda k: P.TRANCHES_AGE[k])
        public = c6.selectbox("Public *", cles_pub,
                              index=cles_pub.index(p.public) if p.public in cles_pub else 0,
                              format_func=lambda k: P.PUBLICS[k])

        st.markdown("**Coordonnées**")
        c7, c8 = st.columns(2)
        telephone = c7.text_input("Téléphone", value=p.telephone or "")
        courriel = c8.text_input("Courriel", value=p.courriel or "")
        adresse = st.text_input("Adresse", value=p.adresse or "")

        st.markdown("**Situation**")
        situation = st.text_input(
            "Classe et établissement, ou situation professionnelle",
            value=p.situation or "",
            placeholder="ex. 3e au collège Jean Moulin — ou : cadre, en rupture "
                        "conventionnelle")
        rqth = st.checkbox("Reconnaissance de la qualité de travailleur handicapé (RQTH)",
                           value=p.rqth)

        requis = (age < P.SEUIL_CONSENTEMENT_PARENTAL) if age is not None \
            else P.MINEUR_PAR_TRANCHE.get(tranche, False)
        mineur = (age < 18) if age is not None else P.MINEUR_PAR_TRANCHE.get(tranche, False)

        representant = representant_contact = ""
        date_cons, recueilli = date.today(), False
        if mineur or requis:
            st.markdown("**Représentant légal**")
            if requis:
                st.warning("Personne mineure : le consentement parental est obligatoire "
                           "avant tout enregistrement.")
            c9, c10 = st.columns(2)
            representant = c9.text_input("Nom du représentant légal",
                                         value=p.representant_legal or "")
            representant_contact = c10.text_input("Téléphone ou courriel du représentant",
                                                  value=p.representant_contact or "")
            recueilli = st.checkbox("Consentement parental recueilli",
                                    value=bool(p.consentement_parental_date),
                                    disabled=not requis)
            date_cons = st.date_input(
                "Date du consentement parental",
                value=_date_ou(p.consentement_parental_date, date.today()),
                format="DD/MM/YYYY", disabled=not (requis and recueilli))

        st.markdown("**Suivi**")
        lien = st.text_input("Lien mescompetences.info (saisie manuelle)",
                             value=p.lien_mescompetences or "")
        notes = st.text_area("Notes libres", value=p.notes_libres or "", height=120)

        if st.form_submit_button("Enregistrer", type="primary"):
            p.nom, p.prenom = nom, prenom
            p.date_naissance = date_naissance
            p.tranche_age, p.public = tranche, public
            p.telephone = telephone.strip() or None
            p.courriel = courriel.strip() or None
            p.adresse = adresse.strip() or None
            p.situation = situation.strip() or None
            p.rqth = rqth
            p.representant_legal = representant.strip() or None
            p.representant_contact = representant_contact.strip() or None
            p.consentement_parental_date = (
                date_cons.isoformat() if (requis and recueilli) else None)
            p.lien_mescompetences = lien.strip() or None
            p.notes_libres = notes.strip() or None
            try:
                P.modifier(p) if existante else P.creer(p)
            except (P.ConsentementParentalManquant, P.DonneesInvalides) as exc:
                st.error(f"Enregistrement bloqué — {exc}")
                return
            st.session_state.pop("page_personne", None)
            st.success(f"Fiche « {p.nom_affiche} » enregistrée.")
            st.rerun()

    if existante:
        etat_completude(existante)


def etat_completude(p: P.Personne) -> None:
    """Rappelle ce qui reste à renseigner, sans bloquer."""
    manquants = p.champs_manquants
    if not manquants:
        st.success("Fiche complète.")
    else:
        st.info("Fiche incomplète — reste à renseigner : " + ", ".join(manquants) + ".")


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
        st.session_state.pop("personne_id", None)
        st.rerun()
    if c2.button("Annuler", key=f"non_{p.id}"):
        st.session_state.pop(cle, None)
        st.rerun()
