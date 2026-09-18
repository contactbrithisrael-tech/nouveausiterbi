# L'EPREUVE DES REPONSES A LA CONVOCATION
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8798 RBI_COURRIEL=1 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-reponses.py
#
# L'ecran de la Tenue portait cet aveu : « Dans la vraie application,
# ces reponses arrivent seules ; ici, cliquez a leur place. » On eprouve
# qu'elles arrivent — de bout en bout : la convocation part avec un lien
# propre a chacun, le Frere clique, et LE COMPTE DES AGAPES bouge sans
# que personne ne depouille un courriel.
#
# CE QUI COMPTE LE PLUS : le lien de reponse ne doit rien ouvrir
# d'autre. Retrouve dans une boite aux lettres, il ne doit donner ni la
# liste des presents, ni les adresses, ni le Tableau.
from playwright.sync_api import sync_playwright
import json, os, tempfile

U = os.environ.get("RBI_URL", "http://127.0.0.1:8798/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []


def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:240]}")
    if not c:
        ko.append(n)


CARNET = {
    "_format": "carnet-loge-rbi", "_version": 1, "_origine": "Epreuve",
    "visiteurs": [{"nom": "TSEDEK", "prenom": "Nekouda", "grade": "M",
                   "loge": "L EXEMPLE", "email": "nekouda@exemple.test"}],
    "amies": [],
    "amis": [{"nom": "RAHAMIM", "prenom": "Tikva", "email": "tikva@exemple.test"}],
}

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context()
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    dlg = []
    pg.on("dialog", lambda d: (dlg.append(d.message), d.accept()))

    chemin = os.path.join(tempfile.gettempdir(), "carnet-reponses.json")
    json.dump(CARNET, open(chemin, "w", encoding="utf-8"), ensure_ascii=False)

    pg.goto(U); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1800)
    pg.click("#t-tableau"); pg.wait_for_timeout(400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU); pg.wait_for_timeout(2500)
    pg.set_input_files("#fichier-sauvegarde", chemin); pg.wait_for_timeout(2500)
    pg.click("#t-tenue"); pg.wait_for_timeout(1200)

    agapes_avant = pg.evaluate("auxAgapesTous()")
    v(agapes_avant == 0, "personne aux agapes avant qu'on ait repondu", agapes_avant)

    # == 1. LA CONVOCATION PART AVEC UN LIEN PAR PERSONNE ============
    pg.evaluate("async () => { await fetch('/__courriels/vider'); }")
    dlg.clear()
    pg.click("#poste-tous"); pg.wait_for_timeout(3500)

    remis = pg.evaluate("async () => (await (await fetch('/__courriels')).json())")
    v(len(remis) == 1, "un seul appel au service", len(remis))
    versions = remis[0]["corps"]["messageVersions"] if remis else []
    v(len(versions) >= 3, "un message par personne", len(versions))

    import re
    liens = []
    for mv in versions:
        t = mv.get("textContent", "") or remis[0]["corps"].get("textContent", "")
        m = re.search(r"/reponse\.html\?j=([a-f0-9]{64})", t)
        if m:
            liens.append((mv["to"][0]["email"], m.group(1)))
    v(len(liens) == len(versions),
      "CHAQUE MESSAGE PORTE UN LIEN DE REPONSE", f"{len(liens)}/{len(versions)}")
    v(len(set(j for _, j in liens)) == len(liens),
      "ET CHACUN LE SIEN : deux personnes n'ont jamais le meme jeton",
      len(set(j for _, j in liens)))
    corps0 = versions[0].get("textContent", "")
    v("agapes" in corps0.lower(), "le message dit a quoi sert le lien", corps0[-260:])

    # == 2. LE LIEN N'OUVRE QUE LA REPONSE ===========================
    jeton = dict((e, j) for e, j in liens)["nekouda@exemple.test"]
    anon = b.new_context().new_page()
    anon.goto(U + "reponse.html?j=" + jeton)
    anon.wait_for_timeout(1500)
    v(anon.locator("#tout").is_visible(), "la page de reponse s'ouvre sans compte")
    v("Nekouda" in anon.inner_text("#nom"), "et sait qui repond",
      anon.inner_text("#nom"))

    fuite = anon.evaluate("""async (j) => {
      const r = await fetch('/api/reponse?j=' + j);
      return JSON.stringify(await r.json()); }""", jeton)
    v("@" not in fuite,
      "AUCUNE ADRESSE NE SORT PAR CE LIEN", fuite[:200])
    for interdit in ["TICHRI", "HECHVAN", "membres", "visiteurs"]:
        v(interdit not in fuite,
          f"ni « {interdit} » : le Tableau reste ferme", fuite[:200])

    sansSession = anon.evaluate("""async () => {
      const r = await fetch('/api/reponses');
      return r.status; }""")
    v(sansSession == 401,
      "ET LA LISTE DES REPONSES EXIGE UNE SESSION : deux routes, deux portes",
      sansSession)

    faux = anon.evaluate("""async () => {
      const r = await fetch('/api/reponse?j=' + 'a'.repeat(64));
      return r.status; }""")
    v(faux == 404, "un jeton invente ne mene nulle part", faux)

    # == 3. ON REPOND ================================================
    anon.click("#present"); anon.wait_for_timeout(1200)
    v(anon.locator("#bloc-agapes").is_visible(),
      "la question des agapes ne parait QU'A CELUI QUI VIENT")
    anon.click("#oui-agapes"); anon.wait_for_timeout(1200)
    v("agapes" in anon.inner_text("#etat"), "la reponse est confirmee a l'ecran",
      anon.inner_text("#etat"))

    # on change d'avis
    anon.click("#excuse"); anon.wait_for_timeout(1200)
    v(anon.locator("#bloc-agapes").is_hidden(),
      "qui s'excuse ne se voit plus demander s'il reste a table")
    etat = anon.evaluate("""async (j) => {
      const r = await fetch('/api/reponse?j=' + j);
      return await r.json(); }""", jeton)
    v(etat["reponse"] == "excuse" and etat["agapes"] is False,
      "ON PEUT CHANGER D'AVIS, et le couvert est retire", etat)
    anon.click("#present"); anon.wait_for_timeout(1000)
    anon.click("#oui-agapes"); anon.wait_for_timeout(1200)

    # == 3bis. LE REGLEMENT DES AGAPES ==============================
    # Il parait a l'instant ou l'on vient de dire qu'on reste a table —
    # le seul moment ou l'on est dispose a le faire. Pas avant : montrer
    # un bouton de paiement a qui s'excuse, c'est reclamer de l'argent
    # a qui ne doit rien.
    LIEN = "https://exemple.test/agapes-du-rite"
    pg.evaluate("(l) => { E.tenue.agapesPaiement = l; garder(); }", LIEN)
    pg.wait_for_timeout(1500)
    a2 = b.new_context().new_page()
    a2.goto(U + "reponse.html?j=" + jeton); a2.wait_for_timeout(1500)
    v(a2.locator("#bloc-paiement").is_visible(),
      "LE REGLEMENT PARAIT A QUI VIENT ET RESTE A TABLE")
    v(a2.get_attribute("#payer", "href") == LIEN,
      "et il mene la ou la Secretaire l'a dit", a2.get_attribute("#payer", "href"))
    a2.click("#non-agapes"); a2.wait_for_timeout(1200)
    v(a2.locator("#bloc-paiement").is_hidden(),
      "QUI NE RESTE PAS NE SE VOIT RIEN RECLAMER")
    a2.click("#excuse"); a2.wait_for_timeout(1200)
    v(a2.locator("#bloc-paiement").is_hidden(), "un excuse non plus")
    a2.close()

    # un lien qui n'est pas une adresse web ne devient pas un bouton
    pg.evaluate("() => { E.tenue.agapesPaiement = 'javascript:alert(1)'; garder(); }")
    pg.wait_for_timeout(1500)
    a3 = b.new_context().new_page()
    a3.goto(U + "reponse.html?j=" + jeton); a3.wait_for_timeout(900)
    d3 = a3.evaluate("""async (j) => {
      const r = await fetch('/api/reponse?j=' + j); return await r.json(); }""", jeton)
    v(d3.get("paiement") in (None, ""),
      "UN LIEN QUI N'EST PAS UNE ADRESSE WEB EST REFUSE PAR LE SERVEUR", d3.get("paiement"))
    a3.close()
    pg.evaluate("(l) => { E.tenue.agapesPaiement = l; garder(); }", LIEN)
    pg.wait_for_timeout(1500)

    # la page de reponse ne laisse toujours rien filtrer du registre
    fuite2 = pg.evaluate("""async (j) => {
      const r = await fetch('/api/reponse?j=' + j);
      return JSON.stringify(await r.json()); }""", jeton)
    v("@" not in fuite2, "et le registre ne filtre toujours pas par cette route",
      fuite2[:160])

    anon.goto(U + "reponse.html?j=" + jeton); anon.wait_for_timeout(1400)
    anon.click("#present"); anon.wait_for_timeout(900)
    anon.click("#oui-agapes"); anon.wait_for_timeout(1200)

    # l'Ami repond aussi
    jetonAmi = dict((e, j) for e, j in liens)["tikva@exemple.test"]
    a2 = b.new_context().new_page()
    a2.goto(U + "reponse.html?j=" + jetonAmi); a2.wait_for_timeout(1500)
    a2.click("#present"); a2.wait_for_timeout(1000)
    a2.click("#oui-agapes"); a2.wait_for_timeout(1200)

    # == 4. LE COMPTE REMONTE AU REGISTRE ============================
    bilan = pg.evaluate("async () => await releverReponses()")
    pg.wait_for_timeout(1200)
    v(bilan and bilan["combien"] >= 2, "les reponses sont reprises au registre", bilan)
    apres = pg.evaluate("auxAgapesTous()")
    v(apres == 2,
      "LE COMPTE DES AGAPES A BOUGE SANS QU'ON DEPOUILLE UN COURRIEL",
      f"{agapes_avant} → {apres}")
    v(pg.evaluate("E.visiteurs.find(x=>x.nom==='TSEDEK').presentTenue") is True,
      "le visiteur est marque attendu par SA propre reponse")
    v(pg.evaluate("(E.agapesVisiteurs||{})[E.visiteurs.find(x=>x.nom==='TSEDEK').id]") is True,
      "et son couvert est compte")
    amis = pg.evaluate("E.reponsesAmis || {}")
    v(any(x.get("agapes") for x in amis.values()),
      "L'AMI AUSSI : le traiteur ne distingue pas les qualites", amis)
    v(pg.evaluate("E.visiteurs.some(x=>x.nom==='RAHAMIM')") is False,
      "mais il n'entre pas d'office au carnet des Visiteurs")

    # deux relevés de suite n'ajoutent rien
    b2 = pg.evaluate("async () => await releverReponses()")
    v(b2 is not None and b2["combien"] == 0,
      "un second releve ne reprend rien : ce qui est verse l'est", b2)

    # une correction a la main n'est pas ecrasee
    pg.evaluate("""() => { const x = E.visiteurs.find(v=>v.nom==='TSEDEK');
      E.agapesVisiteurs[x.id] = false; garder(); }""")
    pg.wait_for_timeout(800)
    b3 = pg.evaluate("async () => await releverReponses()")
    pg.wait_for_timeout(800)
    v(pg.evaluate("E.agapesVisiteurs[E.visiteurs.find(x=>x.nom==='TSEDEK').id]") is False,
      "UNE CORRECTION DE LA SECRETAIRE N'EST PAS ECRASEE au releve suivant")

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
