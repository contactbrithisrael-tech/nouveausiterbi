# L'EPREUVE DES ENVOIS GROUPES
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8794 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-envois.py
#
# LA QUESTION EST SIMPLE : la convocation part-elle a TOUS ?
#
# Tout part par un lien « mailto: ». Le programme n'envoie rien
# lui-meme : il ouvre le logiciel de courrier avec le message deja
# ecrit. Or ce lien a une longueur, et les systemes coupent au-dela
# d'un certain point SANS RIEN DIRE. Un message tronque, c'est une
# convocation partie a la moitie des colonnes sans que personne ne
# s'en apercoive. C'est cela qu'on eprouve ici.
from playwright.sync_api import sync_playwright
import os

U = os.environ.get("RBI_URL", "http://127.0.0.1:8794/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []


def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:220]}")
    if not c:
        ko.append(n)


# de quoi faire un envoi qui deborde : beaucoup d'Amis
CARNET = {
    "_format": "carnet-loge-rbi", "_version": 1, "_origine": "Epreuve",
    "visiteurs": [{"nom": "TSEDEK", "prenom": "Nekouda", "grade": "M",
                   "loge": "L EXEMPLE", "email": "nekouda@exemple.test"}],
    "amies": [],
    "amis": [{"nom": "AMI%02d" % i, "prenom": "Prenom%02d" % i,
              "email": "ami.numero.%02d@exemple-assez-long.test" % i}
             for i in range(60)],
}

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context(permissions=["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    dlg = []
    pg.on("dialog", lambda d: (dlg.append(d.message), d.accept()))

    import json, tempfile
    chemin = os.path.join(tempfile.gettempdir(), "carnet-envois.json")
    json.dump(CARNET, open(chemin, "w", encoding="utf-8"), ensure_ascii=False)

    pg.goto(U); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1500)
    pg.click("#t-tableau"); pg.wait_for_timeout(400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU); pg.wait_for_timeout(2500)

    # == 1. SANS LES AMIS : qui recoit ? ============================
    r = pg.evaluate("""() => ({
      mem: destinatairesMembres().length,
      vis: destinatairesVisiteurs().length,
      ami: destinatairesAmis().length })""")
    v(r["mem"] > 0 and r["vis"] > 0,
      "le Tableau donne des membres et des visiteurs joignables", r)

    # == 2. AVEC LES AMIS : ils entrent dans « tout le monde » ======
    pg.set_input_files("#fichier-sauvegarde", chemin); pg.wait_for_timeout(2500)
    r = pg.evaluate("""() => ({
      mem: destinatairesMembres().length,
      vis: destinatairesVisiteurs().length,
      ami: destinatairesAmis().length,
      tous: sansDoublon(destinatairesMembres()
              .concat(destinatairesVisiteurs())
              .concat(destinatairesAmis())).length })""")
    v(r["ami"] == 60, "les soixante Amis sont joignables", r)
    v(r["tous"] == r["mem"] + r["vis"] + r["ami"],
      "LES AMIS SONT COMPTES DANS « TOUT LE MONDE »", r)

    pg.click("#t-tenue"); pg.wait_for_timeout(700)
    ecran = pg.inner_text("#v-tenue")
    v("Ami" in ecran and str(r["ami"]) in ecran,
      "l'ecran annonce combien d'Amis recevront la convocation", ecran[:400])
    v(("Convoquer tout le monde (%d)" % r["tous"]) in ecran,
      "et le bouton porte le compte exact", ecran[:300])

    # == 3. LA LONGUEUR DU LIEN EST MESUREE =========================
    m = pg.evaluate("""() => {
      const tous = sansDoublon(destinatairesMembres()
        .concat(destinatairesVisiteurs()).concat(destinatairesAmis()));
      return { long: lienCourriel(tous, 'Convocation', convocationTexte()).length,
               court: lienCourriel([], 'Convocation', convocationTexte()).length,
               seuil: LIEN_PRUDENT }; }""")
    v(m["long"] > m["seuil"],
      "a soixante et quelques destinataires, le lien depasse le seuil prudent", m)
    v(m["court"] < m["long"],
      "le lien sans les adresses est plus court : c'est le chemin de repli", m)

    # == 4. LE CHEMIN DE REPLI EST MESURE, LUI AUSSI ================
    # Le defaut trouve en service : on refusait le lien complet, puis on
    # ouvrait le lien SANS ADRESSES sans jamais le mesurer. La convocation
    # pese a elle seule plus de trois mille caracteres : la messagerie
    # ouvrait un brouillon VIDE, et l'on croyait avoir pris le chemin sur.
    v(m["court"] > m["seuil"],
      "la convocation entiere ne tient pas dans un lien, meme sans adresses",
      m)
    dlg.clear()
    pg.click("#mail-tous"); pg.wait_for_timeout(1800)
    ensemble = " ".join(dlg)
    v("Convoquer" in ensemble and "Ami(s) de la Loge" in ensemble,
      "on demande confirmation en detaillant qui recevra", ensemble[:260])
    v("vide" in ensemble,
      "ON NE FAIT PLUS SEMBLANT : on dit que le brouillon s'ouvrirait vide",
      ensemble[:400])
    presse = pg.evaluate("() => navigator.clipboard.readText()")
    v("TENUE" in presse.upper() or "convoqu" in presse.lower(),
      "et c'est LE TEXTE de la convocation qui passe au presse-papier",
      presse[:120])

    # == 4bis. QUAND LE MESSAGE TIENT, LE CHEMIN SUR EST GARDE ======
    # On depouille la convocation jusqu'a ce que le lien sans adresses
    # repasse sous le seuil : la, et la seulement, on ouvre le brouillon
    # sans les adresses et on les met au presse-papier pour la case Cci.
    pg.evaluate("""() => { E.odj = []; E.tenue.motAccueil = '';
      E.tenue.signature = ''; E.tenue.agapesQuiPaie = '';
      E.tenue.agapesPaiement = '';
      if (E.reglages) E.reglages.motFin = ''; garder(); dessiner(); }""")
    pg.wait_for_timeout(800)
    pg.click("#t-tenue"); pg.wait_for_timeout(600)
    c2 = pg.evaluate("() => lienCourriel([], 'Convocation', convocationTexte()).length")
    v(c2 < 2000, "depouillee, la convocation repasse sous le seuil", c2)
    dlg.clear()
    pg.click("#mail-tous"); pg.wait_for_timeout(1800)
    ensemble = " ".join(dlg)
    v("SANS RIEN DIRE" in ensemble,
      "ON PREVIENT QUE LA LISTE POURRAIT ETRE COUPEE EN SILENCE", ensemble[:400])
    v("Cci" in ensemble,
      "et l'on dit exactement quoi faire : coller en copie cachee", ensemble[:400])

    pg.wait_for_timeout(800)
    presse = pg.evaluate("() => navigator.clipboard.readText()")
    v(presse.count("@") >= 60,
      "LES ADRESSES SONT DANS LE PRESSE-PAPIER, toutes",
      str(presse.count("@")) + " adresses")
    v("ami.numero.00@exemple-assez-long.test" in presse,
      "y compris celles des Amis", presse[:120])

    # == 4ter. QUAND L'ATELIER POSTE, ON Y RENVOIE ==================
    # Sur ce serveur le service n'est pas configure ; on le simule pour
    # eprouver le seul chemin qui reste quand la messagerie ne peut rien :
    # renvoyer au bouton qui marche, au lieu d'un brouillon vide.
    pg.set_input_files("#fichier-sauvegarde", chemin); pg.wait_for_timeout(2500)
    # on rend a la convocation sa longueur : c'est elle qui deborde
    pg.evaluate("""() => { E.odj = Array.from({length: 10}, (_, i) =>
      ({ h: '2' + i + ':00', t: 'Point numero ' + i +
         ' de l ordre du jour, ecrit assez long pour peser son poids' }));
      garder(); dessiner(); }""")
    pg.wait_for_timeout(700)
    pg.click("#t-tenue"); pg.wait_for_timeout(500)
    c3 = pg.evaluate("() => lienCourriel([], 'Convocation', convocationTexte()).length")
    v(c3 > 2000, "la convocation entiere redeborde le seuil", c3)
    pg.evaluate("() => { POSTE.su = true; POSTE.configure = true; "
                "POSTE.service = 'brevo'; POSTE.expediteur = 'x@exemple.test'; "
                "dessiner(); }")
    pg.wait_for_timeout(700)
    pg.click("#t-tenue"); pg.wait_for_timeout(700)
    v(pg.locator("#poste-tous").count() == 1,
      "le bouton d'envoi reel parait quand le service est la")
    v("btn-or" in (pg.get_attribute("#poste-tous", "class") or ""),
      "ET C'EST LUI QUI PORTE L'OR : le geste ordinaire est celui qui marche",
      pg.get_attribute("#poste-tous", "class"))
    v("btn-or" not in (pg.get_attribute("#mail-tous", "class") or ""),
      "la messagerie redevient un recours, non le geste ordinaire",
      pg.get_attribute("#mail-tous", "class"))
    dlg.clear()
    pg.click("#mail-tous"); pg.wait_for_timeout(1800)
    ensemble = " ".join(dlg)
    v("Envoyer vraiment" in ensemble,
      "ET L'ON RENVOIE AU BOUTON QUI MARCHE au lieu d'un brouillon vide",
      ensemble[:400])

    # == 5. UN ENVOI COURT PART SANS RIEN DEMANDER ==================
    # on retire les Amis : le lien redevient court
    pg.evaluate("() => { E.amis = []; garder(); dessiner(); }")
    pg.wait_for_timeout(700)
    court = pg.evaluate("""() => {
      const l = sansDoublon(destinatairesMembres().concat(destinatairesVisiteurs()));
      return lienCourriel(l, 'Convocation', convocationTexte()).length; }""")
    v(court > 0, "sans les Amis, le lien se raccourcit", court)

    # == 6. LE BOUTON QUI COPIE, POUR LE CHEMIN SUR ================
    pg.set_input_files("#fichier-sauvegarde", chemin); pg.wait_for_timeout(2500)
    pg.click("#t-tenue"); pg.wait_for_timeout(600)
    v(pg.locator("#copier-adresses").count() == 1,
      "un bouton copie les adresses, sans passer par l'envoi")
    pg.evaluate("() => navigator.clipboard.writeText('rien')")
    dlg.clear()
    pg.click("#copier-adresses"); pg.wait_for_timeout(1200)
    presse2 = pg.evaluate("() => navigator.clipboard.readText()")
    v(presse2.count("@") >= 60, "il les met toutes", presse2.count("@"))
    v(any("presse-papier" in d for d in dlg), "et le dit", dlg[:1])

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
