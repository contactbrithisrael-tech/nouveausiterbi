# L'ÉPREUVE DE L'ANNUAIRE — du formulaire jusqu'au carnet
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8792 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-annuaire.py
#
# CE QU'ON ÉPROUVE. Un Frère remplit le formulaire de l'Espace
# Membres ; sa fiche doit se retrouver au carnet des Visiteurs sans
# que personne n'ouvre un courriel. Et elle doit s'y retrouver POUR CE
# QU'ELLE EST : une déclaration reçue, dont la case « Tuilé par » est
# vide — le tuilage de l'Espace Membres garde le seuil d'une page, pas
# celui du Temple.
#
# On éprouve le VRAI formulaire, servi par le vrai serveur, tuilage
# compris. Une imitation qui lui ressemblerait n'apprendrait rien.
from playwright.sync_api import sync_playwright
import os, json

U = os.environ.get("RBI_URL", "http://127.0.0.1:8792/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []

def v(c, n, d=''):
    print(f"  {'✓' if c else '✗'} {n}{'' if c else '  <- ' + str(d)[:240]}")
    if not c: ko.append(n)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    # ══ 1. UN FRÈRE REMPLIT LE FORMULAIRE ═══════════════════════════
    cF = b.new_context(); F = cF.new_page()
    eF = []; F.on("pageerror", lambda e: eF.append(str(e)))
    F.goto(U + "espace-membres.html"); F.wait_for_timeout(900)

    v(F.locator("#tuilage-porte").is_visible(),
      "l'Espace Membres commence par le tuilage")
    v(not F.locator("#contenu-membres").is_visible(),
      "et ne montre rien avant d'être répondu")

    F.fill("#porte-q1", "de midi a minuit")
    F.fill("#porte-q2", "7 ans")
    F.click("#porte-form button[type=submit]"); F.wait_for_timeout(600)
    v(F.locator("#contenu-membres").is_visible(), "les questions d'usage ouvrent")

    F.click("button.onglet:has-text('Annuaire')"); F.wait_for_timeout(500)
    for champ, valeur in [
        ("prenom", "Reouven"), ("nom", "MISHPAT"),
        ("email", "reouven.mishpat@exemple.test"),
        ("telephone", "06 11 22 33 44"), ("ville", "Aix-en-Provence"),
        ("grade", "Maître"), ("loge", "L∴ EXEMPLE n°01")]:
        F.fill(f"#form-annuaire [name={champ}]", valeur)
    F.check("#form-annuaire input[value=\"Recevoir les convocations\"]")
    F.click("#form-annuaire button[type=submit]"); F.wait_for_timeout(1800)

    # ══ 2. LE REGISTRE L'A REÇUE ════════════════════════════════════
    recu = F.evaluate("""async () => (await (await fetch('/api/annuaire')).json())""")
    v(recu.get("erreur") == "non_connecte",
      "SANS SESSION, ON NE PEUT PAS RELEVER LA BOÎTE : déposer n'est pas lire",
      recu)

    # ══ 3. MARTINE OUVRE SON ÉCRAN ══════════════════════════════════
    cM = b.new_context(); M = cM.new_page()
    eM = []; M.on("pageerror", lambda e: eM.append(str(e)))
    dialogues = []
    M.on("dialog", lambda d: (dialogues.append(d.message), d.accept()))
    M.goto(U); M.wait_for_timeout(900)
    M.fill("#porte-mdp", CLE); M.click("#porte-form button[type=submit]")
    M.wait_for_timeout(2500)

    vis = M.evaluate("E.visiteurs.map(v=>({nom:v.nom,email:v.email,tuilePar:v.tuilePar,"
                     "annuaire:!!v.venuDeLAnnuaire,tel:v.tel,orient:v.orient}))")
    recu2 = [x for x in vis if x["email"] == "reouven.mishpat@exemple.test"]
    v(len(recu2) == 1,
      "LA FICHE EST AU CARNET, sans qu'aucun courriel n'ait été ouvert", vis)
    if recu2:
        f = recu2[0]
        v(f["nom"] == "MISHPAT", "avec son nom", f)
        v(f["tel"] == "06 11 22 33 44", "son téléphone", f)
        v(f["orient"] == "Aix-en-Provence", "et sa ville portée à l'Orient", f)
        v(f["annuaire"] is True, "marquée comme venue de l'annuaire", f)
        v(f["tuilePar"] == "",
          "ET SA CASE « TUILÉ PAR » EST VIDE : le formulaire n'a tuilé personne", f)

    M.click("#t-visiteurs"); M.wait_for_timeout(600)
    t = M.inner_text("#v-visiteurs")
    v("L’annuaire a déposé" in t or "L'annuaire a déposé" in t,
      "l'écran le lui dit — elle n'a rien à aller chercher", t[:220])
    v("pas encore tuilé" in t, "et rappelle ce qui manque", t[:400])

    # ══ 4. LA FILE EST RELEVÉE, PAS VIDÉE DEUX FOIS ═════════════════
    reste = M.evaluate("""async () => (await (await fetch('/api/annuaire',
      {credentials:'same-origin'})).json())""")
    v(reste.get("fiches") == [],
      "la fiche est marquée versée : on ne la reversera pas", reste)

    # ══ 5. DEUX OFFICIERS, UNE SEULE FICHE ══════════════════════════
    # On redépose la MÊME fiche et l'on fait relever un second écran :
    # sans dédoublonnage, le même Frère entrerait deux fois au carnet.
    F.evaluate("""async () => { await fetch('/api/annuaire', { method:'POST',
      headers:{'content-type':'application/json'},
      body: JSON.stringify({ prenom:'Reouven', nom:'MISHPAT',
        email:'reouven.mishpat@exemple.test', obedience:'Obédience d’épreuve' }) }); }""")
    M.wait_for_timeout(300)
    bilan = M.evaluate("async () => await releverAnnuaire()")
    vis2 = M.evaluate("E.visiteurs.filter(v=>v.email==='reouven.mishpat@exemple.test').length")
    v(vis2 == 1, "LE MÊME FRÈRE N'ENTRE PAS DEUX FOIS AU CARNET", vis2)
    v(bilan and bilan["neuves"] == 0 and bilan["completees"] == 1,
      "sa fiche est complétée de ce qui manquait, et rien n'est ajouté", bilan)
    v(M.evaluate("E.visiteurs.find(v=>v.email==='reouven.mishpat@exemple.test').obedience")
      == "Obédience d’épreuve", "l'obédience, absente, a bien été portée")

    # ══ 6. CE QUI NE DOIT PAS ENTRER ════════════════════════════════
    def deposer(corps):
        return F.evaluate("""async (c) => { const r = await fetch('/api/annuaire',
          { method:'POST', headers:{'content-type':'application/json'},
            body: JSON.stringify(c) });
          return { s: r.status, c: await r.json() }; }""", corps)

    r = deposer({"nom": "SANSPRENOM", "email": "x@exemple.test"})
    v(r["s"] == 400 and r["c"]["erreur"] == "nom_manquant",
      "une fiche sans prénom est refusée", r)
    r = deposer({"prenom": "A", "nom": "B", "email": "pas-une-adresse"})
    v(r["s"] == 400 and r["c"]["erreur"] == "courriel_manquant",
      "une adresse qui n'en est pas une est refusée", r)
    r = deposer({"prenom": "A", "nom": "B", "email": "c@exemple.test",
                 "versee": 1, "loge_id": 99, "id": 1,
                 "mechant": "<script>alert(1)</script>"})
    v(r["s"] == 200, "une fiche valable passe", r)
    depose = M.evaluate("""async () => (await (await fetch('/api/annuaire',
      {credentials:'same-origin'})).json())""")
    garde = depose["fiches"][0]["fiche"] if depose.get("fiches") else {}
    v("mechant" not in garde and "versee" not in garde and "loge_id" not in garde,
      "ET SEULS LES CHAMPS ATTENDUS SONT GARDÉS : un formulaire ne décide "
      "pas de ce que porte la base", garde)

    # == 7. UN VISITEUR S'ENREGISTRE AVEC CINQ CHAMPS ================
    # Nom, prenom, grade, courriel, Loge. Tout le reste est facultatif
    # et doit le DIRE : sans quoi l'on cherche ce qu'on n'a pas.
    M.click("#t-visiteurs"); M.wait_for_timeout(500)
    M.click("#vis-nouveau"); M.wait_for_timeout(600)
    for champ, val in [("prenom", "Chimon"), ("nom", "EDOUT"),
                       ("grade", "Compagnon"),
                       ("email", "chimon.edout@exemple.test")]:
        M.fill("#v-" + champ, val); M.wait_for_timeout(100)
    M.wait_for_timeout(900)
    neuf = M.evaluate("E.visiteurs.find(v=>v.email==='chimon.edout@exemple.test')")
    v(neuf is not None,
      "LE VISITEUR EST ENREGISTRE AVEC QUATRE CHAMPS, SANS SA LOGE", neuf)
    # il y a bien une note au bas de la fiche, mais elle explique ce
    # qu'est un visiteur — elle ne reclame rien.
    notes = M.inner_text("#v-visiteurs")
    v("Il manque" not in notes,
      "et rien ne lui reproche ce qu'il n'a pas rempli",
      [x for x in notes.split("\n") if "Il manque" in x])
    v("pas exig" in M.inner_text("#v-visiteurs .sous"),
      "le sous-titre dit que la Loge n'est pas exigee",
      M.inner_text("#v-visiteurs .sous"))

    # la note ne parait que si l'un des QUATRE manque, et elle ne
    # refuse rien : elle dit que la fiche est deja enregistree.
    M.fill("#v-grade", ""); M.wait_for_timeout(900)
    note = M.inner_text("#v-visiteurs .note") if M.locator("#v-visiteurs .note").count() else ""
    v("son grade" in note, "sans le grade, la note le dit", note[:160])
    v("Loge" not in note, "et ne reclame plus la Loge", note[:160])
    v("enregistr" in note and "empêche" in note,
      "en rappelant que la fiche EST enregistree, et que rien n'empeche de l'inscrire",
      note[:200])
    M.fill("#v-grade", "Compagnon"); M.wait_for_timeout(900)

    # les champs facultatifs le disent, les cinq autres non
    for cle, facultatif in [("prenom", False), ("nom", False), ("grade", False),
                            ("email", False),
                            ("loge", True), ("orient", True), ("obedience", True),
                            ("rite", True), ("tel", True), ("invitePar", True),
                            ("tuilePar", True)]:
        lab = M.evaluate(
            "() => { const c = document.querySelector('label[for=\"v-" + cle + "\"]');"
            " return c ? c.textContent : null; }")
        dit = lab is not None and "facultatif" in lab
        v(dit == facultatif,
          "le champ " + cle + (" est marque facultatif" if facultatif
                               else " ne l'est pas : il fait partie des quatre"), lab)

    # == 8. MARQUER VENU SE FAIT D'UN CLIC, DEPUIS LA LISTE ==========
    M.click("#vis-retour"); M.wait_for_timeout(600)
    v(M.locator("button[data-attendu]").count() >= 1,
      "chaque ligne du carnet porte son bouton de presence",
      M.locator("button[data-attendu]").count())

    # le refus dit quoi faire, au lieu de dire non
    M.evaluate("() => { E.visiteurs.forEach(v => v.presentTenue = false); dessiner(); }")
    M.wait_for_timeout(400)
    dialogues.clear()
    M.click("#vis-enregistrer"); M.wait_for_timeout(800)
    dlg = list(dialogues)
    v(bool(dlg) and "Cette tenue" in dlg[0],
      "LE REFUS DIT OU CLIQUER, il ne dit plus seulement non", dlg)
    v(bool(dlg) and "est VENU" in dlg[0],
      "et ce que ce registre note vraiment", dlg)

    # un clic, et la visite se porte au registre
    idv = M.evaluate("E.visiteurs[0].id")
    M.click('button[data-attendu="' + str(idv) + '"]'); M.wait_for_timeout(700)
    lu = "E.visiteurs.find(v=>v.id===" + str(idv) + ")"
    v(M.evaluate(lu + ".presentTenue") is True,
      "UN CLIC SUFFIT A LE MARQUER VENU", M.evaluate(lu + ".presentTenue"))
    v(M.locator("#vis-enregistrer").count() == 1,
      "ET LA FICHE NE S'OUVRE PAS : un bouton dans une ligne cliquable "
      "faisait deux choses a la fois")
    dialogues.clear()
    M.click("#vis-enregistrer"); M.wait_for_timeout(900)
    dlg2 = list(dialogues)
    v(bool(dlg2) and "visite(s) enregistree(s)".replace("ee", "ée") in dlg2[0],
      "et la visite se porte alors au registre", dlg2)
    v(M.evaluate("(" + lu + ".visites||[]).length") >= 1,
      "le registre la porte", M.evaluate(lu + ".visites"))
    v(M.evaluate(lu + ".presentTenue") is False,
      "et la marque retombe : la tenue est passee")

    # == UNE LOGE N'EST PAS UNE PERSONNE ============================
    # Un Atelier qui s'inscrit ne vient pas visiter : il vient
    # CORRESPONDRE. Il donne l'adresse de son secretariat — celle a qui
    # nos convocations partiront — et depose son etat civil. Sa fiche
    # rejoint donc les LOGES AMIES, et surtout PAS les Visiteurs : ce
    # serait porter au carnet des visites un Atelier qui n'est jamais
    # venu.
    L = cF.new_page()
    eL = []; L.on("pageerror", lambda e: eL.append(str(e)))
    L.goto(U + "espace-membres.html"); L.wait_for_timeout(900)
    L.fill("#porte-q1", "de midi a minuit")
    L.fill("#porte-q2", "7 ans")
    L.click("#porte-form button[type=submit]"); L.wait_for_timeout(700)
    L.click("button.onglet:has-text('Inscrire ma Loge')"); L.wait_for_timeout(600)
    v(L.locator("#inscrire-loge").is_visible(),
      "l'Espace Membres porte un onglet « Inscrire ma Loge »")
    for champ, valeur in (("loge_nom", "Les Trois Colonnes"),
                          ("loge_numero", "142"),
                          ("loge_orient", "Marseille"),
                          ("loge_obedience", "GLMF"),
                          ("loge_temple", "Temple Salomon"),
                          ("contact_nom", "Sarah B."),
                          ("contact_email", "secretariat@trois-colonnes.test"),
                          ("contact_tel", "06 11 22 33 44")):
        L.fill("#form-loge [name=" + champ + "]", valeur)
    L.click("#form-loge button[type=submit]"); L.wait_for_timeout(2000)
    v(not eL, "aucune erreur JavaScript au formulaire de Loge", eL)

    M.reload(); M.wait_for_timeout(2600)
    trouvee = M.evaluate(
        "(E.amies||[]).find(x => (x.nom||'').indexOf('Trois Colonnes') >= 0) || null")
    v(trouvee is not None,
      "ET ELLE REJOINT LE CARNET DES LOGES AMIES, non celui des Visiteurs",
      M.evaluate("(E.amies||[]).map(x=>x.nom)"))
    if trouvee:
        v(trouvee.get("nom") == "Les Trois Colonnes n°142",
          "le numero fait partie du nom : deux homonymes ne se confondent pas",
          trouvee.get("nom"))
        v(trouvee.get("contactEmail") == "secretariat@trois-colonnes.test",
          "C'EST LE SECRETARIAT DE L'ATELIER QUI RECEVRA NOS CONVOCATIONS, "
          "non un Frere en particulier", trouvee.get("contactEmail"))
        v(trouvee.get("orient") == "Marseille" and trouvee.get("temple") == "Temple Salomon",
          "et son etat civil suit", trouvee)
    v(M.evaluate("!(E.visiteurs||[]).some(v => (v.nom||'').indexOf('Colonnes')>=0)"),
      "une Loge n'entre PAS au carnet des Visiteurs : elle n'est jamais venue")

    # deux depots ne font pas deux Loges. Le formulaire se ferme une
    # fois envoye : on rouvre la page, comme le ferait un Secretaire
    # qui s'y reprend a deux fois.
    L.reload(); L.wait_for_timeout(1000)
    # le tuilage passe une fois ne se redemande pas : on ne le refait
    # que s'il est la
    if L.locator("#tuilage-porte").is_visible():
        L.fill("#porte-q1", "de midi a minuit")
        L.fill("#porte-q2", "7 ans")
        L.click("#porte-form button[type=submit]"); L.wait_for_timeout(700)
    L.click("button.onglet:has-text('Inscrire ma Loge')"); L.wait_for_timeout(600)
    L.fill("#form-loge [name=loge_nom]", "Les Trois Colonnes")
    L.fill("#form-loge [name=loge_numero]", "142")
    L.fill("#form-loge [name=contact_email]", "secretariat@trois-colonnes.test")
    L.click("#form-loge button[type=submit]"); L.wait_for_timeout(2000)
    M.reload(); M.wait_for_timeout(2600)
    v(M.evaluate("(E.amies||[]).filter(x => (x.nom||'').indexOf('Trois Colonnes')>=0).length") == 1,
      "un second depot ne cree pas une seconde Loge",
      M.evaluate("(E.amies||[]).map(x=>x.nom)"))
    L.close()

    # == LA CHAINE EST-ELLE VIVANTE ? ===============================
    # La liste des fiches ne rend que celles EN ATTENTE : elle est donc
    # vide aussi bien quand tout a ete verse au carnet que quand RIEN
    # n'est jamais arrive. Et rien n'arriverait sans bruit — le
    # formulaire de l'Espace Membres avale son echec volontairement,
    # parce que le courriel part de toute facon. Ce choix protege le
    # Frere qui remplit ; il aveugle la Secretaire, seule a pouvoir y
    # remedier. Elle peut desormais le demander.
    dit = []
    M.on("dialog", lambda d: dit.append(d.message))
    M.click("#t-visiteurs"); M.wait_for_timeout(700)
    v(M.locator("#annuaire-verifier").count() == 1,
      "un bouton demande si l'annuaire du site arrive jusqu'ici")
    dit.clear()
    M.click("#annuaire-verifier"); M.wait_for_timeout(2500)
    ens = " ".join(dit)
    v("fiche" in ens.lower(), "et il repond", ens[:200])
    v("@" not in ens,
      "SANS RIEN LIVRER DU REGISTRE : des nombres, pas des adresses", ens[:200])
    v("vers" in ens.lower() and "attente" in ens.lower(),
      "il separe ce qui est verse au carnet de ce qui attend encore",
      ens[:260])

    v(not eF and not eM, "aucune erreur JavaScript, des deux côtés", eF + eM)
    b.close()

print(f"\n  {len(ko)} échec(s)" if ko else "\n  tout passe")
