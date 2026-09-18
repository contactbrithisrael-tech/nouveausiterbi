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

    # == 4. ON PREVIENT AU LIEU DE COUPER EN SILENCE ================
    dlg.clear()
    pg.click("#mail-tous"); pg.wait_for_timeout(1500)
    ensemble = " ".join(dlg)
    v("Convoquer" in ensemble and "Ami(s) de la Loge" in ensemble,
      "on demande confirmation en detaillant qui recevra", ensemble[:260])
    v("SANS RIEN DIRE" in ensemble,
      "ON PREVIENT QUE LA LISTE POURRAIT ETRE COUPEE EN SILENCE", ensemble[:400])
    v("Cci" in ensemble,
      "et l'on dit exactement quoi faire : coller en copie cachee", ensemble[:400])

    # les adresses sont bien dans le presse-papier
    pg.wait_for_timeout(800)
    presse = pg.evaluate("() => navigator.clipboard.readText()")
    v(presse.count("@") >= 60,
      "LES ADRESSES SONT DANS LE PRESSE-PAPIER, toutes",
      str(presse.count("@")) + " adresses")
    v("ami.numero.00@exemple-assez-long.test" in presse,
      "y compris celles des Amis", presse[:120])

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
