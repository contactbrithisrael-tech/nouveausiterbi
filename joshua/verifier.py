#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérifie la cohérence de la carte du corpus avant de la livrer à Joshua.

Une carte fausse ne se voit pas : elle ouvre simplement un texte au
mauvais degré, ou fait citer une page qui n'existe pas. Ces contrôles
attrapent ce qu'une relecture humaine laisse passer.

    python3 joshua/verifier.py
"""

import json
import os
import sys

ETATS = {"a_fournir", "declare", "indexe"}


def verifier(chemin):
    with open(chemin, encoding="utf-8") as f:
        c = json.load(f)

    fautes = []
    reserves = {}

    degres = c.get("degres", [])
    ouvrages = {o["id"]: o for o in c.get("ouvrages", [])}

    # Le degré ZÉRO — le degré public — n'est pas l'un des trente-trois :
    # il n'a ni nom hébreu, ni Séphira, ni corps d'appartenance. Il est
    # décrit à part, et repris ici pour que les deux contrôles qui
    # suivent — l'état, et la concordance des deux sens — s'appliquent à
    # lui comme aux autres. Sans cela, un ouvrage annoncé au degré zéro
    # passerait pour orphelin.
    public = c.get("degre_public")
    if public is not None:
        if public.get("degre") != 0:
            fautes.append("degre_public : « degre » vaut %r, attendu 0"
                          % public.get("degre"))
        if not public.get("sources"):
            fautes.append("degre_public : aucun ouvrage — le degré zéro "
                          "existe mais ne rend rien")
        if not public.get("atteste_par"):
            fautes.append("degre_public : aucune attestation — un degré "
                          "ouvert sans décision tracée se referme mal")
        degres = list(degres) + [public]

    # ── Les 33 degrés, une fois chacun ────────────────────────────
    numeros = [d.get("degre") for d in degres if d.get("degre") != 0]
    attendus = set(range(1, 34))
    if set(numeros) != attendus:
        manquants = sorted(attendus - set(numeros))
        intrus = sorted(set(numeros) - attendus)
        if manquants:
            fautes.append("degrés absents de la carte : %s" % manquants)
        if intrus:
            fautes.append("degrés hors de la plage 1-33 : %s" % intrus)
    doublons = sorted({n for n in numeros if numeros.count(n) > 1})
    if doublons:
        fautes.append("degrés en double : %s" % doublons)

    # ── Les corps couvrent l'ensemble, sans chevauchement ─────────
    vus = []
    for corps in c.get("corps", []):
        vus.extend(corps.get("degres", []))
    if sorted(vus) != sorted(attendus):
        chevauche = sorted({n for n in vus if vus.count(n) > 1})
        if chevauche:
            fautes.append("degrés rattachés à plusieurs corps : %s" % chevauche)
        orphelins = sorted(attendus - set(vus))
        if orphelins:
            fautes.append("degrés rattachés à aucun corps : %s" % orphelins)

    # ── Chaque degré, pris un par un ──────────────────────────────
    cite = {}
    for d in degres:
        n = d.get("degre")
        etat = d.get("etat")

        if etat not in ETATS:
            fautes.append("degré %s : état inconnu « %s » (attendu : %s)"
                          % (n, etat, ", ".join(sorted(ETATS))))

        sources = d.get("sources", [])

        if etat == "a_fournir" and sources:
            fautes.append("degré %s : marqué « a_fournir » mais porte déjà une source" % n)
        if etat in ("declare", "indexe") and not sources:
            fautes.append("degré %s : marqué « %s » sans aucune source" % (n, etat))

        for s in sources:
            oid = s.get("ouvrage")
            if oid not in ouvrages:
                fautes.append("degré %s : renvoie à l'ouvrage « %s », qui n'est pas déclaré" % (n, oid))
            else:
                cite.setdefault(oid, set()).add(n)
            # Un texte indexé sans pages ne peut pas être cité.
            if etat == "indexe" and not s.get("pages"):
                fautes.append("degré %s : ouvrage « %s » marqué indexé sans pages — "
                              "Joshua ne pourrait citer aucune référence" % (n, oid))
            elif etat == "declare" and not s.get("pages"):
                # Regroupé par ouvrage : une ligne par degré donnerait
                # cent lignes identiques, que plus personne ne lit.
                reserves.setdefault(oid, []).append(n)

    # ── Les deux sens doivent concorder ───────────────────────────
    for oid, o in ouvrages.items():
        annonces = set(o.get("degres_couverts", []))
        citants = cite.get(oid, set())
        if annonces != citants:
            manque = sorted(annonces - citants)
            surplus = sorted(citants - annonces)
            if manque:
                fautes.append("ouvrage « %s » : annonce couvrir les degrés %s, "
                              "qui ne le citent pas" % (oid, manque))
            if surplus:
                fautes.append("ouvrage « %s » : cité par les degrés %s, "
                              "qu'il n'annonce pas couvrir" % (oid, surplus))

    # ── Compte rendu ──────────────────────────────────────────────
    couverts = sorted(n for n in numeros
                      if any(d.get("degre") == n and d.get("etat") != "a_fournir"
                             for d in degres))
    print("Carte du corpus — %s" % chemin)
    print("  degrés cartographiés     : %d" % len(set(numeros)))
    print("  ouvrages déclarés        : %d" % len(ouvrages))
    print("  degrés pourvus d'un texte: %d sur 33  %s" % (len(couverts), couverts or ""))
    print("  degrés en attente        : %d" % (33 - len(couverts)))

    if reserves:
        print("\nPages à renseigner :")
        for oid in sorted(reserves):
            d = reserves[oid]
            plage = ("degrés %d-%d" % (min(d), max(d))) if len(d) > 1 else ("degré %d" % d[0])
            print("  · %-22s %s (%d)" % (oid, plage, len(d)))

    if fautes:
        print("\nINCOHÉRENCES (%d) :" % len(fautes))
        for f in fautes:
            print("  ✗ %s" % f)
        return 1

    print("\nCarte cohérente.")
    return 0


if __name__ == "__main__":
    ici = os.path.dirname(os.path.abspath(__file__))
    sys.exit(verifier(sys.argv[1] if len(sys.argv) > 1
                      else os.path.join(ici, "corpus.json")))
