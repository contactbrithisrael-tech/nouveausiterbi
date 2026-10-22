# L'EPREUVE DU TABLEAU DE LA LOGE
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8810 RBI_COURRIEL=1 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-tableau.py
#
# CE QU'ON EPROUVE. Un onglet du site porte les noms des Soeurs et
# Freres inscrits au Tableau, avec present, absent et agapes — et
# chacun s'y declare lui-meme.
#
# CE QUI DECIDE, ET QU'ON EPROUVE D'ABORD : LA PAGE NE PORTE AUCUN NOM.
# Ce fichier est servi en clair par Cloudflare. Si un seul nom y etait
# ecrit, il serait publie — et l'appartenance maconnique d'une personne
# est une donnee sensible. Les noms viennent du serveur, contre une
# adresse qui figure parmi les convoques, et jamais autrement.
from playwright.sync_api import sync_playwright
import os, tempfile


# Un PDF minuscule mais vrai : en-tete %PDF-, objets, trailer, %%EOF.
# LA CONVOCATION NE PART PLUS SANS PIECE JOINTE — c'est une regle posee
# sur main, et l'epreuve doit s'y plier comme la Secretaire s'y plie.
def faux_pdf():
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n")

U = os.environ.get("RBI_URL", "http://127.0.0.1:8810/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []

def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:300]}")
    if not c: ko.append(n)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    # == 1. LA SECRETAIRE CONVOQUE ==================================
    cM = b.new_context(); M = cM.new_page()
    eM = []; M.on("pageerror", lambda e: eM.append(str(e)))
    M.on("dialog", lambda d: d.accept())
    M.goto(U); M.wait_for_timeout(800)
    M.fill("#porte-mdp", CLE); M.click("#porte-form button[type=submit]")
    M.wait_for_timeout(2200)
    M.set_input_files("#fichier-sauvegarde", TABLEAU); M.wait_for_timeout(2600)
    LE_JOUR = M.evaluate("E.tenue.date")
    gens = M.evaluate("convocables().map(x => [x.prenoms + ' ' + x.nom, x.email])")
    gens = [(n, e) for n, e in gens if e]
    v(len(gens) >= 3, "l'Atelier a des colonnes avec une adresse", len(gens))
    MOI_NOM, MOI_MAIL = gens[0]
    print("  ·", len(gens), "convocables · la Tenue est au", LE_JOUR)

    M.click("#t-tenue"); M.wait_for_timeout(1000)
    # La piece d'abord : sans PDF joint, la convocation ne part pas.
    pdf = os.path.join(tempfile.gettempdir(), "Convocation epreuve tableau.pdf")
    open(pdf, "wb").write(faux_pdf())
    M.set_input_files("#fichier-piece", pdf); M.wait_for_timeout(1600)
    M.click("#poste-tous"); M.wait_for_timeout(4500)
    lignes = M.evaluate("async () => (await (await fetch('/__table?nom=reponses'))"
                        ".json())")
    v(isinstance(lignes, list) and len(lignes) >= 3,
      "les convocations sont parties, et chacune a sa ligne de reponse",
      len(lignes) if isinstance(lignes, list) else lignes)

    # == 2. LA PAGE NE PORTE AUCUN NOM ==============================
    cV = b.new_context(); V = cV.new_page()
    eV = []; V.on("pageerror", lambda e: eV.append(str(e)))
    V.goto(U + "espace-membres.html"); V.wait_for_timeout(900)
    source = V.content()
    fuites = [n for n, _ in gens if n.split()[-1] in source]
    v(not fuites,
      "AUCUN NOM DE MEMBRE N'EST ECRIT DANS LA PAGE : elle est servie en clair, "
      "un nom ici serait publie", fuites)
    adresses = [e for _, e in gens if e in source]
    v(not adresses, "ni aucune adresse", adresses)

    if V.locator("#tuilage-porte").is_visible():
        V.fill("#porte-q1", "de midi a minuit")
        V.fill("#porte-q2", "7 ans")
        V.click("#porte-form button[type=submit]"); V.wait_for_timeout(700)
    V.click("button.onglet:has-text('Tableau de la Loge')"); V.wait_for_timeout(600)
    v(V.locator("#tableau-loge").is_visible(), "l'onglet s'ouvre")
    v(not V.locator("#tableau-vu").is_visible(),
      "ET NE MONTRE RIEN AVANT QU'ON SE SOIT PRESENTE")

    # == 3. UNE ADRESSE INCONNUE N'OUVRE RIEN =======================
    V.fill("#t-courriel", "personne@nulle-part.test")
    V.click("#form-tableau button[type=submit]"); V.wait_for_timeout(1400)
    v(not V.locator("#tableau-vu").is_visible(),
      "UNE ADRESSE INCONNUE N'OUVRE PAS LE TABLEAU")
    v(V.locator("#tableau-ennui").is_visible(), "et l'ennui est dit")
    dit = V.inner_text("#tableau-ennui")
    v("convoqu" in dit, "il dit pourquoi, et quoi faire", dit[:200])
    for n, _ in gens:
        if n.split()[-1] in V.content(): ko.append("un nom a fuite sur refus")
    v("un nom a fuite sur refus" not in ko,
      "ET AUCUN NOM N'A FUITE : un refus n'apprend rien")

    # == 4. SON ADRESSE OUVRE LE TABLEAU ============================
    V.fill("#t-courriel", MOI_MAIL)
    V.click("#form-tableau button[type=submit]"); V.wait_for_timeout(1600)
    v(V.locator("#tableau-vu").is_visible(),
      "SON ADRESSE OUVRE LE TABLEAU", V.inner_text("#tableau-ennui")
      if V.locator("#tableau-ennui").is_visible() else "")
    liste = V.inner_text("#tableau-liste")
    manquants = [n for n, _ in gens if n.split()[-1] not in liste]
    v(not manquants, "et toutes les colonnes y sont nommees", manquants)
    # Les intitules sont mis en capitales par la feuille de style : on
    # compare sans tenir compte de la casse, sinon l'epreuve echoue sur
    # une majuscule et non sur ce qu'elle veut verifier.
    for col in ["présence", "agapes"]:
        v(col in liste.lower(), f"avec sa colonne « {col} »")
    v(MOI_NOM.split()[-1] in V.inner_text("#tableau-moi"),
      "il se reconnait sur sa propre ligne", V.inner_text("#tableau-moi")[:160])

    # CE QUI SORT, ET RIEN DE PLUS
    rendu = V.evaluate("""async (mail) => { const r = await fetch('/api/tableau',
      { method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({ courriel: mail }) }); return await r.json(); }""",
      MOI_MAIL)
    brut = str(rendu)
    autres = [e for _, e in gens if e != MOI_MAIL and e in brut]
    v(not autres, "LE SERVEUR NE REND AUCUNE ADRESSE : le nom, la reponse, les "
      "agapes — et c'est tout", autres)
    v("jeton" not in brut, "ni aucun jeton : on ne peut pas repondre pour un autre",
      brut[:200])
    v("tel" not in brut and "du" not in str(rendu.get("tableau")),
      "ni le telephone, ni la tresorerie")

    # == 5. IL SE DECLARE LUI-MEME ==================================
    v(V.locator("#tableau-agapes").is_visible() is False,
      "les agapes ne se posent pas avant qu'on ait dit venir : demander a un "
      "absent s'il reste a table ferait compter un couvert")
    V.click("#tableau-loge button[data-rep='present']"); V.wait_for_timeout(1500)
    v(V.locator("#tableau-agapes").is_visible(),
      "une fois present, la question des agapes parait")
    V.click("#tableau-loge button[data-agapes='oui']"); V.wait_for_timeout(1500)
    moi = V.evaluate("""async (mail) => { const r = await fetch('/api/tableau',
      { method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({ courriel: mail }) });
      return (await r.json()).moi; }""", MOI_MAIL)
    v(moi.get("reponse") == "present" and moi.get("agapes") is True,
      "SA DECLARATION EST ENREGISTREE : present, et un couvert", moi)
    v("Présent" in V.inner_text("#tableau-liste"),
      "et le Tableau la montre a tous ceux qui l'ouvrent")
    v("couvert" in V.inner_text("#tableau-compte"),
      "le compte des couverts est dit", V.inner_text("#tableau-compte")[:200])

    # S'EXCUSER EFFACE LE COUVERT : compter un couvert pour un absent,
    # c'est le payer.
    V.click("#tableau-loge button[data-rep='excuse']"); V.wait_for_timeout(1500)
    moi2 = V.evaluate("""async (mail) => { const r = await fetch('/api/tableau',
      { method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({ courriel: mail }) });
      return (await r.json()).moi; }""", MOI_MAIL)
    v(moi2.get("reponse") == "excuse" and moi2.get("agapes") is None,
      "S'EXCUSER EFFACE LE COUVERT : un couvert commande pour un absent est paye",
      moi2)
    V.click("#tableau-loge button[data-rep='present']"); V.wait_for_timeout(1200)
    V.click("#tableau-loge button[data-agapes='oui']"); V.wait_for_timeout(1400)

    # == 6. LA SECRETAIRE LE RELEVE PAR LE CHEMIN QUI EXISTE ========
    # On n'a invente aucun stockage : c'est la meme ligne que le lien
    # personnel de la convocation, et son programme la releve deja.
    M.reload(); M.wait_for_timeout(3000)
    rep = M.evaluate(f"""() => {{
      const m = convocables().find(x => (x.email||'').toLowerCase()
        === '{MOI_MAIL.lower()}');
      return m ? {{ rep: rep(m.id), agapes: !!(E.agapes||{{}})[m.id] }} : null; }}""")
    v(rep and rep.get("rep") == "present",
      "CE QU'IL A DECLARE ARRIVE AU REGISTRE DE L'ATELIER, sans fusion nouvelle",
      rep)
    v(rep and rep.get("agapes") is True, "et son couvert est compte", rep)

    # == 7. ON N'ESSAIE PAS LES ADRESSES AU HASARD ==================
    bloc = None
    for i in range(45):
        bloc = V.evaluate("""async (i) => { const r = await fetch('/api/tableau',
          { method:'POST', headers:{'content-type':'application/json'},
            body: JSON.stringify({ courriel: 'x' + i + '@essai.test' }) });
          return { s: r.status, c: await r.json() }; }""", i)
        if bloc["s"] == 429: break
    v(bloc and bloc["s"] == 429 and bloc["c"].get("erreur") == "trop_dessais",
      "L'ESSAI D'ADRESSES AU HASARD EST ARRETE", bloc)
    v(V.evaluate("""async (mail) => { const r = await fetch('/api/tableau',
        { method:'POST', headers:{'content-type':'application/json'},
          body: JSON.stringify({ courriel: mail }) }); return r.status; }""",
        MOI_MAIL) == 429,
      "et la porte se ferme pour tous pendant une heure — puis se rouvre seule")

    v(not eV, "aucune erreur JavaScript sur le site", eV)
    v(not eM, "aucune erreur JavaScript a l'ecran de la Secretaire", eM)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
raise SystemExit(1 if ko else 0)
