"""Passation d'un questionnaire pendant la séance.

Une fonction d'affichage par forme. Chacune renvoie (réponses, synthèse) ;
la synthèse est le texte qui atterrira dans le compte rendu.
"""
from __future__ import annotations

import streamlit as st

import questionnaire as Q


def _coches(items, prefixe, avec_definition=False) -> list[str]:
    retenus = []
    gauche, droite = st.columns(2)
    moitie = (len(items) + 1) // 2
    for colonne, lot in ((gauche, items[:moitie]), (droite, items[moitie:])):
        for it in lot:
            libelle = it["texte"]
            if avec_definition and it.get("definition"):
                libelle += f" — *{it['definition']}*"
            if colonne.checkbox(libelle, key=f"{prefixe}_{it['id']}"):
                retenus.append(it["id"])
    return retenus


def checklist(q: Q.Questionnaire) -> tuple[dict, str]:
    retenus = _coches(q.items, q.cle, avec_definition=True)
    textes = [it["texte"] for it in q.items if it["id"] in retenus]
    synthese = (f"{q.titre} — {len(textes)} élément(s) retenu(s) : "
                + " ; ".join(textes)) if textes else ""
    return {"coches": retenus}, synthese


def choix_groupes(q: Q.Questionnaire) -> tuple[dict, str]:
    reponses, lignes = {}, []
    for section in q.sections:
        st.markdown(f"**{section['titre']}**")
        for question in section["questions"]:
            choisis = st.multiselect(question["texte"], question["choix"],
                                     key=f"{q.cle}_{question['id']}")
            if choisis:
                reponses[question["id"]] = choisis
                lignes.append(f"{question['texte']} : " + ", ".join(choisis))
    return reponses, "\n".join(lignes)


def selection_n(q: Q.Questionnaire) -> tuple[dict, str]:
    n = q.nb_a_selectionner
    libelles = {it["texte"]: it["id"] for it in q.items}
    choisis = st.multiselect(f"Sélectionnez-en {n}", list(libelles),
                             key=f"{q.cle}_sel")
    if len(choisis) != n:
        st.caption(f"{len(choisis)} / {n} sélectionné(s).")
    ids = [libelles[t] for t in choisis]
    comptes = Q.profils_par_selection(q, ids)
    lignes = [f"{len(ids)} motivation(s) retenue(s) : " + " ; ".join(choisis), ""]
    for nom, total in comptes:
        if total:
            lignes.append(f"{nom} — {total} item(s) : {q.profils[nom]['description']}")
    if comptes and comptes[0][1]:
        st.info(f"Profil dominant : **{comptes[0][0]}** ({comptes[0][1]} items) — "
                f"{q.profils[comptes[0][0]]['description']}")
    return {"choisis": ids, "profils": dict(comptes)}, "\n".join(lignes) if ids else ""


def likert(q: Q.Questionnaire) -> tuple[dict, str]:
    niveaux = [n["libelle"] for n in q.echelle]
    reponses = {}
    for it in q.items:
        reponses[it["id"]] = st.radio(f"{it['id']}. {it['texte']}", niveaux,
                                      horizontal=True, index=None,
                                      key=f"{q.cle}_{it['id']}")
    donnees = {k: v for k, v in reponses.items() if v}
    if len(donnees) < len(q.items):
        st.caption(f"{len(donnees)} / {len(q.items)} réponse(s).")
        return {"reponses": donnees}, ""
    score = Q.score_likert(q, donnees)
    st.success(f"Score : {score['total']} / {score['maximum']}")
    lignes = [f"Score : {score['total']} / {score['maximum']}",
              score.get("lecture", "")]
    if not score["thematiques"]:
        st.caption("Moyennes par thématique non calculées : le document source ne "
                   "précise pas quels items s'y rattachent.")
    for nom, moyenne in score["thematiques"].items():
        lignes.append(f"{nom} : {moyenne} / 4")
    return {"reponses": donnees, "score": score}, "\n".join(l for l in lignes if l)


def ab(q: Q.Questionnaire) -> tuple[dict, str]:
    reponses = {}
    for it in q.items:
        choix = st.radio(f"**{it['id']}.**", ["A", "B"], horizontal=True, index=None,
                         key=f"{q.cle}_{it['id']}",
                         captions=[it["a"], it["b"]])
        if choix:
            reponses[it["id"]] = choix
    if len(reponses) < len(q.items):
        st.caption(f"{len(reponses)} / {len(q.items)} réponse(s).")
        return {"reponses": reponses}, ""
    scores = Q.score_ab(q, reponses)
    lignes = []
    for axe in q.axes:
        total = scores[axe["nom"]]
        lecture = axe["lecture"]
        sens = lecture["haut"] if total > lecture["seuil"] else lecture["bas"]
        st.info(f"**{axe['nom']}** : {total} — {sens}")
        lignes.append(f"{axe['nom']} : {total} — {sens}")
    if q.get("avertissement"):
        lignes.append(q.avertissement)
    return {"reponses": reponses, "scores": scores}, "\n".join(lignes)


def matrice_360(q: Q.Questionnaire) -> tuple[dict, str]:
    evaluateur = st.selectbox("Colonne à renseigner", q.evaluateurs,
                              key=f"{q.cle}_qui")
    memoire = st.session_state.setdefault(f"{q.cle}_donnees", {})
    courant = memoire.setdefault(evaluateur, {})
    for groupe in q.groupes:
        with st.expander(groupe["titre"], expanded=False):
            for it in groupe["items"]:
                valeur = st.radio(it["texte"], q.niveaux, horizontal=True,
                                  index=q.niveaux.index(courant[it["id"]])
                                  if it["id"] in courant else None,
                                  key=f"{q.cle}_{evaluateur}_{it['id']}")
                if valeur:
                    courant[it["id"]] = valeur
    remplies = {e: len(v) for e, v in memoire.items() if v}
    st.caption("Colonnes renseignées : "
               + (", ".join(f"{e} ({n})" for e, n in remplies.items()) or "aucune"))
    lignes = []
    for groupe in q.groupes:
        for it in groupe["items"]:
            avis = {e: v[it["id"]] for e, v in memoire.items() if it["id"] in v}
            if len(set(avis.values())) > 1:
                lignes.append(f"{it['texte']} — écarts : "
                              + ", ".join(f"{e} {n}" for e, n in avis.items()))
    entete = f"{q.titre} — {sum(remplies.values())} appréciation(s)."
    if lignes:
        entete += "\nÉcarts de perception entre évaluateurs :"
    return {"par_evaluateur": memoire}, "\n".join([entete] + lignes)


def questions_ouvertes(q: Q.Questionnaire) -> tuple[dict, str]:
    if q.get("exemple_accroche"):
        st.caption(q.exemple_accroche)
    entete = {}
    if q.get("entete"):
        colonnes = st.columns(len(q.entete))
        for colonne, champ in zip(colonnes, q.entete):
            entete[champ] = colonne.text_input(champ, key=f"{q.cle}_{champ}")
    reponses, lignes = {}, []
    for it in q.items:
        texte = st.text_area(it["texte"], height=90, key=f"{q.cle}_{it['id']}")
        if texte.strip():
            reponses[it["id"]] = texte.strip()
            lignes.append(f"{it['texte']}\n{texte.strip()}")
    renseigne = [f"{k} : {v}" for k, v in entete.items() if v.strip()]
    return ({"entete": entete, "reponses": reponses},
            "\n\n".join(renseigne + lignes))


AFFICHAGES = {
    "checklist": checklist, "choix_groupes": choix_groupes,
    "selection_n": selection_n, "likert": likert, "ab": ab,
    "matrice_360": matrice_360, "questions_ouvertes": questions_ouvertes,
}


def passer(q: Q.Questionnaire) -> tuple[dict, str]:
    """Affiche le questionnaire et renvoie (réponses brutes, synthèse)."""
    st.subheader(q.titre)
    if q.get("introduction"):
        st.caption(q.introduction)
    if q.get("consigne"):
        st.markdown(f"*{q.consigne}*")
    if q.get("note"):
        st.warning(q.note)
    reponses, synthese = AFFICHAGES[q.forme](q)
    for etape in q.get("suite", []):
        st.caption(f"À faire ensuite : {etape}")
    return reponses, synthese
