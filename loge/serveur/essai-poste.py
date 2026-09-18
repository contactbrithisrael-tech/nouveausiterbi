# L'EPREUVE DU SERVICE D'ENVOI
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   export RBI_PAGE=/tmp/page-epreuve.html
#   RBI_PORT=8795 RBI_COURRIEL=1 node loge/serveur/faux-serveur.mjs &   # avec service
#   RBI_PORT=8796                 node loge/serveur/faux-serveur.mjs &   # sans service
#   RBI_PORT=8797 RBI_COURRIEL=1 RBI_COURRIEL_ECHEC=1 \
#     node loge/serveur/faux-serveur.mjs &                                # service qui refuse
#   python3 loge/serveur/essai-poste.py
#
# AUCUN COURRIEL NE PART PENDANT CETTE EPREUVE. Les appels vers Brevo
# et Resend sont interceptes par le faux serveur, qui garde ce qui LEUR
# AURAIT ETE remis. C'est cela qu'on verifie : la liste exacte, le
# sujet, le corps — et ce que le programme fait quand le service refuse.
#
# CE QUI COMPTE LE PLUS ICI : les destinataires ne viennent PAS de la
# requete. Une route qui accepterait une liste d'adresses serait un
# relais ouvert — il suffirait d'une session pour faire partir
# n'importe quoi vers n'importe qui, sous le nom de la Loge.
from playwright.sync_api import sync_playwright
import json, os, tempfile

AVEC = os.environ.get("RBI_URL_AVEC", "http://127.0.0.1:8795/")
SANS = os.environ.get("RBI_URL_SANS", "http://127.0.0.1:8796/")
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
    "amis": [{"nom": "RAHAMIM", "prenom": "Tikva", "email": "tikva@exemple.test"},
             {"nom": "SHALOM", "prenom": "Ora", "email": "ora@exemple.test"}],
}


def entrer(pg, url):
    pg.goto(url); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1800)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    chemin = os.path.join(tempfile.gettempdir(), "carnet-poste.json")
    json.dump(CARNET, open(chemin, "w", encoding="utf-8"), ensure_ascii=False)

    # ══ 1. SANS SERVICE : ON NE PROPOSE RIEN ════════════════════════
    c0 = b.new_context(); s0 = c0.new_page()
    e0 = []; s0.on("pageerror", lambda e: e0.append(str(e)))
    s0.on("dialog", lambda d: d.accept())
    entrer(s0, SANS)
    s0.click("#t-tableau"); s0.wait_for_timeout(400)
    s0.set_input_files("#fichier-sauvegarde", TABLEAU); s0.wait_for_timeout(2500)
    s0.click("#t-tenue"); s0.wait_for_timeout(900)
    v(s0.evaluate("POSTE.configure") is False,
      "SANS SERVICE CONFIGURE, le programme le sait", s0.evaluate("POSTE.configure"))
    v(s0.locator("#poste-tous").count() == 0,
      "et ne propose PAS d'envoi reel : pas de bouton qui n'aboutirait pas")
    v(s0.locator("#mail-tous").count() == 1,
      "l'ancien chemin reste — la messagerie ouverte a la main")
    s0.close(); c0.close()

    # ══ 2. AVEC SERVICE : LE BOUTON PARAIT ══════════════════════════
    c1 = b.new_context(); pg = c1.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    dlg = []; pg.on("dialog", lambda d: (dlg.append(d.message), d.accept()))
    entrer(pg, AVEC)
    pg.click("#t-tableau"); pg.wait_for_timeout(400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU); pg.wait_for_timeout(2500)
    pg.set_input_files("#fichier-sauvegarde", chemin); pg.wait_for_timeout(2500)
    pg.click("#t-tenue"); pg.wait_for_timeout(1200)

    v(pg.evaluate("POSTE.configure") is True, "AVEC SERVICE, le programme le sait")
    v(pg.evaluate("POSTE.expediteur") == "epreuve@exemple.test",
      "et connait l'expediteur", pg.evaluate("POSTE.expediteur"))
    v(pg.locator("#poste-tous").count() == 1, "le bouton d'envoi reel parait")
    ecran = pg.inner_text("#v-tenue")
    v("epreuve@exemple.test" in ecran,
      "l'ecran dit d'ou partiront les messages", ecran[:400])

    attendu = pg.evaluate("""() => sansDoublon(destinatairesMembres()
      .concat(destinatairesVisiteurs()).concat(destinatairesAmis())).length""")

    # ══ 3. ON ENVOIE ════════════════════════════════════════════════
    pg.evaluate("async () => { await fetch('/__courriels/vider'); }")
    dlg.clear()
    pg.click("#poste-tous"); pg.wait_for_timeout(3000)
    ensemble = " ".join(dlg)
    v("POUR DE BON" in ensemble, "on previent que l'envoi est irreversible", ensemble[:200])
    v("Rien ne s'annule" in ensemble, "et qu'il ne s'annule pas", ensemble[:220])

    remis = pg.evaluate("async () => (await (await fetch('/__courriels')).json())")
    v(len(remis) == 1, "UN SEUL APPEL AU SERVICE pour tout le monde", len(remis))
    if remis:
        c = remis[0]["corps"]
        v(remis[0]["service"] == "brevo", "le service configure est celui-la",
          remis[0]["service"])
        v(len(c.get("messageVersions", [])) == attendu,
          "UN MESSAGE PAR PERSONNE, et le compte y est",
          str(len(c.get("messageVersions", []))) + " pour " + str(attendu))
        adrs = [x["to"][0]["email"] for x in c["messageVersions"]]
        v("tikva@exemple.test" in adrs and "ora@exemple.test" in adrs,
          "LES AMIS DE LA LOGE Y SONT", adrs[:6])
        v("nekouda@exemple.test" in adrs, "les visiteurs aussi")
        v(c["sender"]["email"] == "epreuve@exemple.test",
          "l'expediteur est celui du serveur, non celui de la requete")
        # EXPEDIER N'EST PAS RECEVOIR. On peut expedier depuis un
        # domaine qui n'a aucune boite aux lettres — c'est ce qui rend
        # l'operation gratuite. Mais une convocation appelle des
        # reponses : elles doivent aller vers une boite qu'on releve.
        v(c.get("replyTo", {}).get("email") == "reponses@exemple.test",
          "ET LES REPONSES VONT VERS UNE BOITE QU'ON RELEVE, "
          "non vers le neant", c.get("replyTo"))
        v("TENUE D'OBLIGATION" in c.get("textContent", ""),
          "et le corps est bien la convocation", c.get("textContent", "")[:120])
        # On cherche le CHAMP bcc, non les trois lettres : « bcc » est
        # une suite hexadecimale valable, et un jeton de reponse sur
        # sept en porte une par hasard. L'epreuve accusait alors une
        # copie cachee qui n'existait pas.
        v('"bcc"' not in json.dumps(c).lower(),
          "personne n'est en copie cachee de personne : chacun a son message",
          [k for k in json.dumps(c).lower().split('"') if k == 'bcc'])

    v("remise(s) au service" in ensemble, "on rend compte de ce qui est parti", ensemble[-300:])
    v("ne veut pas dire" in ensemble,
      "EN DISANT CE QUE CELA VEUT DIRE : remise n'est pas lue", ensemble[-300:])

    # ══ 4. LES DESTINATAIRES NE VIENNENT PAS DE LA REQUETE ══════════
    r = pg.evaluate("""async () => {
      const x = await fetch('/api/envoyer', { method:'POST',
        credentials:'same-origin', headers:{'content-type':'application/json'},
        body: JSON.stringify({ groupe:'tous', sujet:'Essai',
          corps:'Essai', destinataires:['inconnu@ailleurs.test'] }) });
      return { s: x.status, c: await x.json() }; }""")
    remis2 = pg.evaluate("async () => (await (await fetch('/__courriels')).json())")
    envoyes = [x["to"][0]["email"] for x in remis2[-1]["corps"]["messageVersions"]]
    v("inconnu@ailleurs.test" not in envoyes,
      "UNE ADRESSE GLISSEE DANS LA REQUETE N'EST PAS SERVIE : "
      "ce n'est pas un relais ouvert", envoyes[:4])
    v(r["c"].get("parties") == attendu,
      "seuls les destinataires du registre sont servis", r["c"])

    # groupe inconnu, sujet vide, corps vide
    for corps, attenduErr in [
            ({"groupe": "n-importe-quoi", "sujet": "x", "corps": "y"}, "groupe_inconnu"),
            ({"groupe": "tous", "sujet": "", "corps": "y"}, "sujet_manquant"),
            ({"groupe": "tous", "sujet": "x", "corps": "   "}, "corps_manquant")]:
        rr = pg.evaluate("""async (c) => {
          const x = await fetch('/api/envoyer', { method:'POST',
            credentials:'same-origin', headers:{'content-type':'application/json'},
            body: JSON.stringify(c) });
          return { s: x.status, c: await x.json() }; }""", corps)
        v(rr["c"].get("erreur") == attenduErr,
          "refus dit : " + attenduErr, rr)

    # sans session, rien
    c2 = b.new_context(); anon = c2.new_page()
    anon.goto(AVEC); anon.wait_for_timeout(700)
    ra = anon.evaluate("""async () => {
      const x = await fetch('/api/envoyer', { method:'POST',
        headers:{'content-type':'application/json'},
        body: JSON.stringify({ groupe:'tous', sujet:'x', corps:'y' }) });
      return x.status; }""")
    v(ra == 401, "SANS SESSION, ON NE FAIT RIEN PARTIR", ra)
    anon.close(); c2.close()

    # ══ 5. LA TRACE ═════════════════════════════════════════════════
    trace = pg.evaluate("""async () => {
      const x = await fetch('/api/etat', {credentials:'same-origin'});
      return x.status; }""")
    v(trace == 200, "le registre reste lisible apres l'envoi", trace)

    # == 6. LE SERVICE REFUSE : ON NE FAIT PAS SEMBLANT ==============
    # C'est le cas qui compte le plus. Un envoi qui echoue et qu'on
    # annonce reussi laisse croire l'Atelier convoque alors que
    # personne n'a rien recu.
    ECHEC = os.environ.get("RBI_URL_ECHEC", "http://127.0.0.1:8797/")
    c3 = b.new_context(); ec = c3.new_page()
    e3 = []; ec.on("pageerror", lambda e: e3.append(str(e)))
    d3 = []; ec.on("dialog", lambda d: (d3.append(d.message), d.accept()))
    entrer(ec, ECHEC)
    ec.click("#t-tableau"); ec.wait_for_timeout(400)
    ec.set_input_files("#fichier-sauvegarde", TABLEAU); ec.wait_for_timeout(2500)
    ec.click("#t-tenue"); ec.wait_for_timeout(1200)
    v(ec.locator("#poste-tous").count() == 1,
      "le service repond, donc le bouton parait")
    d3.clear()
    ec.click("#poste-tous"); ec.wait_for_timeout(3500)
    dit = " ".join(d3)
    v("0 convocation(s) remise" in dit,
      "AUCUNE N'EST ANNONCEE COMME PARTIE", dit[-400:])
    v("REFUS" in dit.upper(), "et les refus sont dits", dit[-400:])
    v("cle refusee" in dit,
      "avec la raison telle que le service l'a donnee, non une invention",
      dit[-400:])
    ec.close(); c3.close()

    # == 4. UN JETON QU'ON N'A PAS RELU N'EST PAS UN JETON ==========
    # La panne la plus traitre de la chaine : l'ecriture des liens de
    # reponse echoue SANS RIEN DIRE. L'INSERT rend la main, le courriel
    # part avec un lien que rien ne connait, et cent personnes tombent
    # sur « ce lien ne mene nulle part » en croyant que c'est leur
    # messagerie qui l'a coupe. Mieux vaut ne rien envoyer.
    MUET = os.environ.get("RBI_URL_MUET", "http://127.0.0.1:8802/")
    c4 = b.new_context(); mu = c4.new_page()
    e4 = []; mu.on("pageerror", lambda e: e4.append(str(e)))
    mu.on("dialog", lambda d: d.accept())
    entrer(mu, MUET)
    mu.click("#t-tableau"); mu.wait_for_timeout(400)
    mu.set_input_files("#fichier-sauvegarde", TABLEAU); mu.wait_for_timeout(2500)
    rep = mu.evaluate("""async () => {
      const r = await fetch('/api/envoyer', { method:'POST',
        headers:{'content-type':'application/json'},
        body: JSON.stringify({ sujet:'Convocation', corps:'Texte',
          groupe:'tous', reponse:true, tenue: E.tenue.date }) });
      return { statut: r.status, corps: await r.text() }; }""")
    v(rep["statut"] == 500,
      "QUAND LES JETONS NE S'ENREGISTRENT PAS, LA ROUTE REFUSE", rep)
    v("jetons_non_enregistres" in rep["corps"],
      "et elle dit laquelle des pannes c'est", rep["corps"][:200])
    v("004-reponses" in rep["corps"],
      "avec de quoi la reparer, non une formule vague", rep["corps"][:240])
    partis = mu.evaluate("""async () => {
      const r = await fetch('/__courriels'); return (await r.json()).length; }""")
    v(partis == 0,
      "ET SURTOUT : PAS UN SEUL COURRIEL N'EST PARTI avec un lien mort",
      f"{partis} courriel(s)")
    mu.close(); c4.close()

    v(not errs and not e0 and not e3 and not e4,
      "aucune erreur JavaScript", errs + e0 + e3 + e4)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
