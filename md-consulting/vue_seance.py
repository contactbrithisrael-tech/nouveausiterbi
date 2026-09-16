"""Écran de séance : chronomètre, outils passés, accès au compte rendu."""
from __future__ import annotations

from datetime import date as _date, datetime

import streamlit as st

import personne as P
import questionnaire as Q
import resultat_test as RT
import seance as S


def _rafraichissant(fonction):
    """Rafraîchit le chronomètre toutes les 30 s si Streamlit sait le faire."""
    fragment = getattr(st, "fragment", None)
    return fragment(run_every="30s")(fonction) if fragment else fonction


def liste_seances(pers: P.Personne) -> None:
    st.subheader("Séances")
    if st.button("▶ Démarrer une séance maintenant", type="primary"):
        s = S.Seance(pers.id)
        s.demarrer()
        S.creer(s)
        st.session_state["seance_id"] = s.id
        st.rerun()
    for s in S.lister_par_personne(pers.id):
        c1, c2, c3 = st.columns([3, 3, 2])
        c1.write(f"**{s.date}**" + (f" — {s.heure_debut[:5]}" if s.heure_debut else ""))
        c2.caption(s.objectif_texte or "objectif non renseigné")
        if c3.button("Ouvrir", key=f"sea_{s.id}", use_container_width=True):
            st.session_state["seance_id"] = s.id
            st.rerun()


@_rafraichissant
def chronometre(s: S.Seance) -> None:
    etat = s.etat()
    libelle = S.libelle_chrono(s)
    if etat == S.NON_DEMARREE:
        st.info(f"Séance non démarrée — {libelle}")
    elif etat == S.EN_COURS:
        st.success(f"⏱ {libelle}")
    elif etat == S.VIGILANCE:
        restant = max(0, s.chrono_max_minutes - int(s.minutes_ecoulees()))
        st.warning(f"⏱ {libelle} — il reste {restant} min.")
    else:
        depasse = int(s.minutes_ecoulees()) - s.chrono_max_minutes
        st.error(f"⏱ {libelle} — plafond dépassé de {depasse} min.")
    minutes = s.minutes_ecoulees() or 0
    st.progress(min(1.0, minutes / max(1, s.chrono_max_minutes)))


def entete_seance(s: S.Seance, pers: P.Personne) -> None:
    st.subheader(f"Séance du {s.date} — {pers.pseudonyme}")
    chronometre(s)
    if not s.heure_debut and st.button("Démarrer le chronomètre"):
        s.demarrer()
        S.modifier(s)
        st.rerun()
    with st.form("entete_seance"):
        objectif = st.text_area("Objectif de la séance", value=s.objectif_texte or "",
                                height=80)
        plafond = st.number_input("Durée maximale (minutes)", 15, 240,
                                  value=s.chrono_max_minutes, step=15)
        if st.form_submit_button("Enregistrer"):
            s.objectif_texte = objectif.strip() or None
            s.chrono_max_minutes = int(plafond)
            S.modifier(s)
            st.rerun()


def outils(s: S.Seance) -> None:
    st.subheader("Outils utilisés")
    for r in RT.lister_par_seance(s.id):
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"**{RT.TYPES.get(r.type_test, r.type_test)}** — "
                    f"{r.date_saisie[:10]}")
        if r.synthese_texte:
            c1.caption(r.synthese_texte)
        if c2.button("Retirer", key=f"del_{r.id}"):
            RT.supprimer(r.id)
            st.rerun()

    dispo = Q.disponibles()
    manquants = [c for c in RT.TYPES_INVESTIGATION if c not in dispo]
    if manquants:
        st.info("Module Investigation : aucun questionnaire n'est installé "
                f"({', '.join(RT.TYPES_INVESTIGATION[c] for c in manquants)}). "
                "Déposez les fichiers dans `questionnaires/` — voir "
                "`docs/questionnaires.md`.")

    with st.form("ajout_outil", clear_on_submit=True):
        cles = list(RT.TYPES_EXTERNES) + list(dispo)
        choix = st.selectbox("Ajouter un outil", cles,
                             format_func=lambda k: RT.TYPES.get(k, k))
        synthese = st.text_area(
            "Synthèse qualitative (pas de scores bruts)", height=100,
            help="Pour un test passé à l'extérieur, seule la synthèse est conservée.")
        if st.form_submit_button("Ajouter"):
            try:
                RT.creer(RT.ResultatTest(s.id, choix,
                                         synthese_texte=synthese.strip() or None))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.rerun()
