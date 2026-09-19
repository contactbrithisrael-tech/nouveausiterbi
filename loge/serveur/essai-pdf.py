# L'EPREUVE DE LA CONVOCATION PRETE A EXPEDIER
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8799 RBI_COURRIEL=1 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-pdf.py
#
# Deux reproches, et ils tiennent tous les deux :
#
#   « les lettres apparaissent presque transparentes » — on MESURE le
#   contraste de chaque texte du document sur son papier blanc, au lieu
#   de le trouver joli a l'ecran.
#
#   « la convocation une fois validee doit etre en pdf pour etre prete
#   a expedier » — on eprouve qu'elle part VRAIMENT en piece jointe, et
#   que ce qu'on joint est vraiment un PDF.
from playwright.sync_api import sync_playwright
import os, tempfile

U = os.environ.get("RBI_URL", "http://127.0.0.1:8799/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []


def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:260]}")
    if not c:
        ko.append(n)


# Un PDF minuscule mais vrai : en-tete %PDF-, objets, xref, %%EOF.
def faux_pdf():
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n")


# Ce que le document doit tenir : 7 pour 1 pour le petit texte, la
# regle de l'accessibilite. Sous 4,5 un mot n'est plus lu, il est devine.
MESURE = """() => {
  const p = document.querySelector('.papier');
  const lum = c => { const f = x => (x/=255) <= 0.03928 ? x/12.92
      : Math.pow((x+0.055)/1.055, 2.4);
    return 0.2126*f(c[0]) + 0.7152*f(c[1]) + 0.0722*f(c[2]); };
  const fond = 1;  /* le papier est blanc */
  const sortie = [];
  for (const el of p.querySelectorAll('*')){
    const propre = [...el.childNodes]
      .filter(n => n.nodeType === 3 && n.textContent.trim().length > 1)
      .map(n => n.textContent.trim()).join(' ');
    if (!propre) continue;
    const c = getComputedStyle(el).color.match(/\\d+/g).map(Number);
    const l = lum(c);
    sortie.push({ texte: propre.slice(0, 44),
                  ratio: Math.round(((fond + 0.05) / (l + 0.05)) * 100) / 100 });
  }
  return sortie;
}"""

# L'ECRAN DE L'APPLICATION EST SOMBRE, LE PAPIER EST BLANC.
#
# On mesure donc dans LES DEUX THEMES. La premiere version de cette
# epreuve ne mesurait qu'en clair, et laissait passer le pire defaut
# du programme : sans doctype, le navigateur tourne en mode quirks, ou
# les TABLEAUX N'HERITENT PAS de la couleur de leur parent. L'en-tete
# et l'ordre du jour, qui sont des tableaux, s'ecrivaient en ivoire sur
# blanc pour qui regardait en mode sombre — 1,2 pour 1. On a longtemps
# cru a des couleurs trop pales ; c'etait une ligne manquante.
THEME = os.environ.get("RBI_THEME", "light")

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_context(viewport={"width": 1280, "height": 1000},
                       color_scheme=THEME).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    dlg = []
    pg.on("dialog", lambda d: (dlg.append(d.message), d.accept()))

    pg.goto(U); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1800)
    pg.click("#t-tableau"); pg.wait_for_timeout(400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU); pg.wait_for_timeout(2500)

    # == 1. L'ENCRE ==================================================
    pg.click("#t-convoc"); pg.wait_for_timeout(700)
    pg.click("#imp-convoc"); pg.wait_for_timeout(900)
    v(pg.evaluate("document.compatMode") == "CSS1Compat",
      "LE PROGRAMME EST EN MODE STANDARD, non en mode quirks : sans quoi "
      "les tableaux des documents prennent la couleur du body",
      pg.evaluate("document.compatMode"))
    v(pg.evaluate("getComputedStyle(document.querySelector('.papier table')).color")
      == "rgb(20, 17, 12)",
      "et les tableaux du papier portent l'encre du papier, non celle de l'ecran",
      pg.evaluate("getComputedStyle(document.querySelector('.papier table')).color"))

    mesures = pg.evaluate(MESURE)
    v(len(mesures) >= 15, "la convocation porte bien du texte a mesurer", len(mesures))
    pales = [m for m in mesures if m["ratio"] < 7]
    v(not pales,
      "CHAQUE LIGNE DE LA CONVOCATION TIENT 7 POUR 1 SUR LE BLANC",
      [(m["texte"], m["ratio"]) for m in pales][:4])
    v(min(m["ratio"] for m in mesures) >= 7,
      "y compris la plus pale de toutes",
      min((m["ratio"], m["texte"]) for m in mesures))

    for doc, bouton in [("emargement", "#imp-emarg"), ("planche", "#imp-planche")]:
        pg.click("#fermer"); pg.wait_for_timeout(200)
        pg.click("#t-tenue"); pg.wait_for_timeout(500)
        pg.click(bouton); pg.wait_for_timeout(800)
        m2 = pg.evaluate(MESURE)
        p2 = [x for x in m2 if x["ratio"] < 7]
        v(not p2, f"et la {doc} aussi : aucune ligne sous 7 pour 1",
          [(x["texte"], x["ratio"]) for x in p2][:3])

    # == 2. LE FICHIER PORTE LE NOM DU DOCUMENT ======================
    pg.click("#fermer"); pg.wait_for_timeout(200)
    pg.click("#t-convoc"); pg.wait_for_timeout(500)
    pg.click("#imp-convoc"); pg.wait_for_timeout(700)
    pg.evaluate("""() => { window.__titres = [];
      window.print = () => window.__titres.push(document.title); }""")
    avant = pg.title()
    pg.click("#tel-pdf"); pg.wait_for_timeout(1400)
    titres = pg.evaluate("window.__titres || []")
    v(len(titres) == 1, "le bouton demande bien une impression", titres)
    v(titres and titres[0].startswith("Convocation"),
      "ET LE FICHIER S'APPELLERA « Convocation… », non « Secretariat »", titres)
    v(pg.title() == avant, "le titre de la page est rendu ensuite", pg.title())

    # == 3. LA PIECE JOINTE ==========================================
    # Le bloc d'envoi est sur l'ecran de la Tenue, avec les convocations.
    pg.click("#fermer"); pg.wait_for_timeout(300)
    pg.click("#t-tenue"); pg.wait_for_timeout(800)

    pas_pdf = os.path.join(tempfile.gettempdir(), "convocation.pdf")
    open(pas_pdf, "wb").write(b"Ceci n'est pas un PDF, quoi qu'en dise son nom.\n")
    dlg.clear()
    pg.set_input_files("#fichier-piece", pas_pdf); pg.wait_for_timeout(1200)
    v(any("n’est pas un PDF" in d for d in dlg),
      "UN FICHIER RENOMME .pdf N'EST PAS JOINT : on lit les octets, non le nom", dlg)
    v(pg.evaluate("PIECE.nom") is None, "et rien n'est retenu", pg.evaluate("PIECE.nom"))

    vrai = os.path.join(tempfile.gettempdir(), "Convocation Bereshit.pdf")
    open(vrai, "wb").write(faux_pdf())
    dlg.clear()
    pg.set_input_files("#fichier-piece", vrai); pg.wait_for_timeout(1400)
    v(not dlg, "un vrai PDF est accepte sans un mot", dlg)
    v(pg.evaluate("PIECE.nom") == "Convocation Bereshit.pdf",
      "la piece est retenue sous son nom", pg.evaluate("PIECE.nom"))
    v("Convocation Bereshit.pdf" in pg.inner_text("#v-tenue"),
      "et l'ecran dit ce qui partira")

    # == 3bis. LA PIECE PORTE LE FEUILLET : LE MESSAGE NE LE RECOPIE PLUS
    # Recopier tout le feuillet dans le corps, c'est le dire deux fois —
    # et c'est cette copie qui pese trois mille caracteres et fait
    # deborder les liens mailto. Le message garde ce qu'aucun PDF ne
    # donne : le mot de la Secretaire, la date, ET LES LIENS.
    court = pg.evaluate("() => corpsConvocation()")
    v("ci-joint" in court,
      "AVEC LA PIECE, LE MESSAGE ANNONCE LA CONVOCATION AU LIEU DE LA RECOPIER",
      court[:160])
    v("ORDRE DU JOUR" not in court,
      "l'ordre du jour n'est plus recopie : il est dans la piece", court[:300])
    v(len(court) < 1800,
      "et le message tient desormais dans un lien de messagerie",
      str(len(court)) + " caracteres")

    # les liens, eux, restent : on ne clique pas sur du papier
    pg.evaluate("() => { E.tenue.agapesPaiement = 'https://exemple.test/agapes'; "
                "E.tenue.motFin = 'Inscrivez-vous sur www.brith-israel.org, "
                "Espace Membres.'; garder(); dessiner(); }")
    pg.wait_for_timeout(600)
    court = pg.evaluate("() => corpsConvocation()")
    v("exemple.test/agapes" in court,
      "LE LIEN DE PAIEMENT RESTE DANS LE MESSAGE", court[-400:])
    v("https://www.brith-israel.org" in court,
      "ET UNE ADRESSE EN « www... » DEVIENT UN VRAI LIEN : sans schema, "
      "plusieurs messageries n'en font pas un lien du tout", court[-400:])

    # sans piece, le texte complet reste le seul porteur
    pg.evaluate("() => { const b = document.getElementById('piece-retirer'); "
                "if (b) b.click(); }")
    pg.wait_for_timeout(700)
    complet = pg.evaluate("() => corpsConvocation()")
    v("ORDRE DU JOUR" in complet,
      "SANS PIECE, LE TEXTE COMPLET REPART : rien d'autre ne porte le feuillet",
      complet[:200])
    pg.set_input_files("#fichier-piece", vrai); pg.wait_for_timeout(1400)

    # == 4. ELLE PART AVEC LA CONVOCATION ============================
    pg.evaluate("async () => { await fetch('/__courriels/vider'); }")
    dlg.clear()
    pg.click("#poste-tous"); pg.wait_for_timeout(3500)
    v(any("Convocation Bereshit.pdf" in d for d in dlg),
      "on est averti de ce qu'on joint AVANT que cela parte", dlg[:1])

    remis = pg.evaluate("async () => (await (await fetch('/__courriels')).json())")
    v(len(remis) == 1, "un seul appel au service", len(remis))
    piece = remis[0]["corps"].get("attachment") if remis else None
    v(isinstance(piece, list) and len(piece) == 1,
      "LA CONVOCATION EN PDF EST BIEN PARTIE, une seule fois pour tous", piece)
    v(piece and piece[0]["name"] == "Convocation Bereshit.pdf",
      "sous son nom", piece[0]["name"] if piece else None)
    import base64
    v(piece and base64.b64decode(piece[0]["content"])[:5] == b"%PDF-",
      "et c'est bien un PDF qui arrive au service")
    v(len(remis[0]["corps"]["messageVersions"]) > 1,
      "chacun la recoit", len(remis[0]["corps"].get("messageVersions", [])))

    # == 5. LE SERVEUR NE CROIT PAS LE PROGRAMME =====================
    forge = pg.evaluate("""async () => {
      const r = await fetch('/api/envoyer', { method: 'POST',
        headers: {'content-type':'application/json'},
        body: JSON.stringify({ groupe: 'membres', sujet: 'Essai',
          corps: 'Essai', piece: { nom: 'piege.pdf', contenu: btoa('MZ programme') } }) });
      return { s: r.status, c: await r.json() }; }""")
    v(forge["s"] == 413 and forge["c"].get("erreur") == "piece_pas_un_pdf",
      "UNE PIECE FORGEE EST REFUSEE PAR LE SERVEUR AUSSI : on ne s'en remet "
      "pas au seul controle de l'ecran", forge)

    mauvais_nom = pg.evaluate("""async () => {
      const r = await fetch('/api/envoyer', { method: 'POST',
        headers: {'content-type':'application/json'},
        body: JSON.stringify({ groupe: 'membres', sujet: 'Essai',
          corps: 'Essai', piece: { nom: 'piege.exe', contenu: btoa('%PDF-1.4') } }) });
      return { s: r.status, c: await r.json() }; }""")
    v(mauvais_nom["c"].get("erreur") == "piece_pas_un_pdf",
      "et une piece qui ne s'appelle pas .pdf ne passe pas davantage", mauvais_nom)

    # == 6. ON PEUT LA RETIRER =======================================
    pg.evaluate("() => { const b = document.getElementById('piece-retirer'); if (b) b.click(); }")
    pg.wait_for_timeout(700)
    v(pg.evaluate("PIECE.nom") is None, "la piece se retire", pg.evaluate("PIECE.nom"))
    v(pg.evaluate("PIECE.contenu") is None, "et son contenu avec elle")

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  [{THEME}] {len(ko)} echec(s)" if ko else f"\n  [{THEME}] tout passe")
