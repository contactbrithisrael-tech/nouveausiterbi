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
    dM = []; M.on("dialog", lambda d: (dM.append(d.message), d.accept()))
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

    # == 6bis. LA DATE DE LA TENUE NE S'ECRIT PLUS EN DUR ===========
    # Elle etait cachee et figee dans la page. La consequence qu'on
    # mesure ici n'est pas « une date passee » : c'est que le
    # formulaire SE RETIRAIT passe cette date et ne revenait qu'a la
    # main — une Tenue de plus, et plus personne ne pouvait s'annoncer,
    # sans que rien ne le dise.
    dite = V.evaluate("""async () => (await (await fetch('/api/tableau')).json())""")
    v(dite.get("tenue") == LE_JOUR,
      "LA ROUTE REND LA DATE DU REGISTRE, et c'est bien celle de la Tenue",
      (dite, LE_JOUR))
    v(set(dite.keys()) == {"tenue"},
      "ET STRICTEMENT ELLE : ni le lieu, ni l'heure, ni un nom", list(dite.keys()))
    sans = V.evaluate("""async () => { const r = await fetch('/api/tableau');
      return r.status; }""")
    v(sans == 200, "elle repond sans session : un Visiteur n'en a pas", sans)

    # LA TENUE DU TABLEAU D'EPREUVE EST PASSEE : le formulaire doit se
    # retirer, et le dire. C'est le bon comportement, et on l'eprouve
    # pour ce qu'il est — non comme un defaut.
    import datetime as _dt
    auj = _dt.date.today().isoformat()
    V.click("button.onglet:has-text('Annoncer ma venue')"); V.wait_for_timeout(1600)
    if LE_JOUR < auj:
        v(not V.locator("#form-venue").is_visible(),
          "UNE TENUE PASSEE NE S'ANNONCE PLUS : le formulaire se retire")
        v(V.locator("#venue-close").is_visible(),
          "et la page dit pourquoi, au lieu de laisser une page muette")

    # ET IL REVIENT TOUT SEUL A LA TENUE SUIVANTE. C'est le point :
    # avant, il fallait rouvrir le fichier et changer la date a la main.
    DEMAIN = (_dt.date.today() + _dt.timedelta(days=30)).isoformat()
    M.evaluate("(d) => { E.tenue.date = d; garder(); }", DEMAIN)
    M.wait_for_timeout(1500)
    V.reload(); V.wait_for_timeout(900)
    if V.locator("#tuilage-porte").is_visible():
        V.fill("#porte-q1", "de midi a minuit"); V.fill("#porte-q2", "7 ans")
        V.click("#porte-form button[type=submit]"); V.wait_for_timeout(700)
    V.click("button.onglet:has-text('Annoncer ma venue')"); V.wait_for_timeout(1800)
    v(V.locator("#form-venue").is_visible(),
      "LE FORMULAIRE REVIENT DE LUI-MEME A LA TENUE SUIVANTE, sans qu'on "
      "rouvre le fichier")
    v(V.input_value("#venue-date") == DEMAIN,
      "IL EN PORTE LA DATE, et le Visiteur la VOIT : un champ cache fait "
      "signer sans lire", V.input_value("#venue-date"))
    v(V.get_attribute("#venue-date", "readonly") is not None,
      "elle est en lecture seule tant que le registre en annonce une")
    v("registre" in V.inner_text("#venue-date-mot"),
      "et la page dit d'ou elle vient", V.inner_text("#venue-date-mot"))

    # L'ENCADRE RESTE ECRIT A LA MAIN : s'il ne parle plus de la meme
    # Tenue, on le DIT. Deux dates qui se contredisent en silence sont
    # pires qu'une seule, fut-elle fausse.
    v(V.get_attribute("#venue-encadre", "data-fin") != DEMAIN,
      "(l'encadre de la page parle bien d'une autre Tenue)")
    v("plus à jour" in V.inner_text("#venue-encadre"),
      "L'ENCADRE PERIME EST SIGNALE, non laisse a lire : son heure, son lieu "
      "et son triangle ne sont plus ceux de la Tenue annoncee",
      V.inner_text("#venue-encadre")[:300])

    # on remet la Tenue d'epreuve ou elle etait
    M.evaluate(f"() => {{ E.tenue.date = '{LE_JOUR}'; garder(); }}")
    M.wait_for_timeout(1200)

    # == 6ter. L'ERRATUM NE VAUT PLUS POUR UNE SEULE TENUE ==========
    # Les phrases validees sont gardees mot pour mot ; ce sont les
    # FAITS qui viennent de la fiche. Changer de Tenue ne change donc
    # pas une syllabe du texte relu — cela change la date annoncee.
    suj = M.evaluate("erratumSujet()")
    v(LE_JOUR.split('-')[2].lstrip('0') in suj and "2026" in suj,
      "L'OBJET DE L'ERRATUM PORTE LA DATE DE LA TENUE EN COURS", suj)
    corps = M.evaluate("erratumCorps()")
    for phrase in ["bien vouloir nous en excuser", "annule et remplace",
                   "Pour mémoire"]:
        v(phrase in corps, f"la phrase validée « {phrase} » est gardée", corps[:200])
    v(M.evaluate("E.tenue.lieuNom") in corps,
      "et les faits viennent de la fiche, non d'une phrase recopiee", corps[-400:])

    # On change la Tenue : le texte suit, sans qu'on touche a rien.
    ancien = suj
    M.evaluate("() => { E.tenue.date = '2027-04-19'; garder(); }")
    M.wait_for_timeout(400)
    suj2 = M.evaluate("erratumSujet()")
    v(suj2 != ancien and "2027" in suj2,
      "CHANGER DE TENUE CHANGE L'ERRATUM : il n'est plus mort le lendemain",
      (ancien, suj2))
    v("bien vouloir nous en excuser" in M.evaluate("erratumCorps()"),
      "et les phrases validees, elles, n'ont pas bouge")
    M.evaluate(f"() => {{ E.tenue.date = '{LE_JOUR}'; garder(); }}")
    M.wait_for_timeout(400)

    # LE VERROU EST DEPLACE, NON LEVE : un erratum sans premier envoi
    # annoncerait une correction a des gens qui n'ont rien recu.
    M.evaluate("() => { E.convoquee = false; garder(); dessiner(); }")
    M.wait_for_timeout(600)
    M.click("#t-tenue"); M.wait_for_timeout(800)
    dM.clear()
    M.click("#poste-erratum"); M.wait_for_timeout(1200)
    ditE = " ".join(dM)
    v("AUCUNE CONVOCATION" in ditE and "Rien n" in ditE,
      "SANS PREMIER ENVOI, L'ERRATUM REFUSE — et dit quoi faire a la place",
      ditE[:300])
    M.evaluate("() => { E.convoquee = true; garder(); dessiner(); }")
    M.wait_for_timeout(500)

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
