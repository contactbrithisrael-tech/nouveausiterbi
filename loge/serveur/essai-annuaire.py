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

    F.fill("#porte-q1", "de la loge de St Jean")
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
    M.on("dialog", lambda d: d.accept())
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

    v(not eF and not eM, "aucune erreur JavaScript, des deux côtés", eF + eM)
    b.close()

print(f"\n  {len(ko)} échec(s)" if ko else "\n  tout passe")
