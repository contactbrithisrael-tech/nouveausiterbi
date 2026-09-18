# L'ÉPREUVE DES DOCUMENTS
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-documents.py
#
# TROIS EXIGENCES, POSÉES PAR LE SOUVERAIN GRAND COMMANDEUR :
#   1. tout document de Bereshit porte sa qualité et son contreseing ;
#   2. les Visiteurs émargent sur UNE PAGE ENTIÈRE, et non sur trois
#      lignes au bas de la feuille des membres ;
#   3. la convocation porte le point du Temple.
from playwright.sync_api import sync_playwright
import os, re

U = os.environ.get("RBI_URL", "http://127.0.0.1:8787/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []

def v(c, n, d=''):
    print(f"  {'✓' if c else '✗'} {n}{'' if c else '  <- ' + str(d)[:220]}")
    if not c: ko.append(n)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context(); pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    pg.goto(U); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1500)
    pg.click("#t-tableau"); pg.wait_for_timeout(400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU); pg.wait_for_timeout(2200)

    PAGE = pg.content()

    def doc(bouton, onglet=None):
        if onglet: pg.click(onglet); pg.wait_for_timeout(400)
        pg.click(bouton); pg.wait_for_timeout(700)
        h = pg.inner_html("#papier"); t = pg.inner_text("#papier")
        pg.click("#fermer"); pg.wait_for_timeout(250)
        return h, t

    # ══ 1. L'AUTORITÉ EN TÊTE, LA SIGNATURE SUR LA SEULE PLANCHE ════
    # L'en-tête dit déjà « sous l'autorité du Souverain Grand
    # Commandeur 33° ». Un pavé « Vu et contresigné » au pied de
    # chaque document répétait la même chose, et coûtait des lignes.
    # Une seule pièce se signe de sa main : la planche à tracer, qui
    # est le procès-verbal des travaux.
    #
    # Le Tableau d'épreuve porte un membre marqué « Souverain Grand
    # Commandeur » : c'est exprès, pour vérifier qu'aucun nom ne
    # remonte sur le papier.

    for nom, bouton, onglet in [
        ("la convocation",          "#imp-convoc", "#t-convoc"),
        ("la feuille d'émargement", "#imp-emarg",  "#t-tenue"),
        ("le carnet des visiteurs", "#imp-carnet", "#t-visiteurs"),
    ]:
        h, t = doc(bouton, onglet)
        v("Vu et contresigné" not in t,
          f"{nom} ne porte PLUS de pavé de contreseing au pied", t[-200:])
        v("Souverain Grand Commandeur 33°" in t,
          f"{nom} porte l'autorité — en tête, une seule fois")
        # une fois par en-tête : l'émargement en a deux, une par feuille
        entetes = t.count("A∴L∴G∴D∴G∴A∴D∴L∴U∴")
        v(t.count("Souverain Grand Commandeur") == entetes,
          f"{nom} le dit une fois par en-tête, et pas davantage",
          f"{t.count('Souverain Grand Commandeur')} pour {entetes} en-tête(s)")
        # ELOUL est un NOM DE MEMBRE du Tableau d'épreuve : il a toute
        # sa place dans une liste de présents. Ce qu'on vérifie, c'est
        # qu'aucun nom ne soit accolé à la charge.
        suites = [t.split(x, 1)[1][:60] for x in ["Souverain Grand Commandeur"]
                  if x in t]
        v(all("ELOUL" not in q and "Lamed" not in q for q in suites),
          f"{nom} : AUCUN NOM n'est accolé à la charge", suites)

    # ── LA PLANCHE À TRACER, ELLE, SE SIGNE ────────────────────────
    h, t = doc("#imp-planche", "#t-tenue")
    v("Signatures du Collège des Trois Lumières" in t,
      "la planche porte les Trois Lumières")
    apres3 = t.split("Second Surveillant")[-1]
    v("Souverain Grand Commandeur du Rite Brith Israël 33°" in apres3,
      "ET LA SIGNATURE DU SOUVERAIN GRAND COMMANDEUR, après elles", apres3[:200])
    v("ELOUL" not in apres3 and "Lamed" not in apres3,
      "sans nom imprimé : la main qui signe dit le reste", apres3[:200])
    bloc = h.split("contreseing")[-1]
    v('class="sig"' in bloc, "avec sa ligne pour signer")

    # ── L'EN-TÊTE : l'autorité, et ב∴ס∴ד∴ en haut à droite ─────────
    pg.click("#t-convoc"); pg.wait_for_timeout(400)
    pg.click("#imp-convoc"); pg.wait_for_timeout(900)
    t = pg.inner_text("#papier")
    v("sous l’autorité du Souverain Grand Commandeur 33°" in t,
      "l'en-tête de chaque document annonce son autorité")
    v(t.count("ב∴ס∴ד∴") == 1,
      "ב∴ס∴ד∴ figure UNE fois — il n'est pas écrit deux fois sur la page",
      t.count("ב∴ס∴ד∴"))
    # on mesure PENDANT que le document est ouvert : une fois refermé,
    # le papier n'a plus ni largeur ni position, et tout mesurerait zéro.
    place = pg.evaluate("""() => {
      const P = document.getElementById('papier');
      const rp = P.getBoundingClientRect();
      const el = [...P.querySelectorAll('div')]
        .find(d => d.textContent.trim() === 'ב∴ס∴ד∴');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const entete = P.querySelector('table').getBoundingClientRect();
      return { centre: Math.round(r.left + r.width / 2 - rp.left),
               milieu: Math.round(rp.width / 2),
               depuisLeHaut: Math.round(r.top - entete.top),
               hauteurEntete: Math.round(entete.height) };
    }""")
    pg.click("#fermer"); pg.wait_for_timeout(250)
    v(place is not None, "on le retrouve dans l'en-tête", place)
    v(place and place["centre"] > place["milieu"],
      "IL EST À DROITE : son milieu passe celui du feuillet", place)
    v(place and place["depuisLeHaut"] <= 6,
      "ET EN HAUT : rien de l'en-tête ne le précède", place)

    # ── la planche s'enregistre SANS le contreseing : sans quoi il
    #    s'ajouterait de nouveau à chaque ouverture
    pg.click("#t-tenue"); pg.wait_for_timeout(400)
    pg.click("#imp-planche"); pg.wait_for_timeout(700)
    # la planche s'enregistre d'elle-même à la frappe
    pg.evaluate("""() => { const c = document.getElementById('corps');
      c.innerHTML += '<p>Un mot ajouté par la Secrétaire.</p>';
      c.dispatchEvent(new Event('input', {bubbles:true})); }""")
    pg.wait_for_timeout(1500)
    enreg = pg.evaluate("E.plancheTexte || ''")
    v(enreg.count("Souverain Grand Commandeur") == 1,
      "la planche enregistrée porte sa ligne de signature UNE fois",
      enreg.count("Souverain Grand Commandeur"))
    pg.click("#fermer"); pg.wait_for_timeout(300)
    pg.click("#imp-planche"); pg.wait_for_timeout(700)
    t2 = pg.inner_text("#papier")
    v(t2.count("Souverain Grand Commandeur du Rite Brith Israël 33°") == 1,
      "et rouvrir la planche ne la double pas",
      t2.count("Souverain Grand Commandeur du Rite Brith Israël 33°"))
    v("Un mot ajouté par la Secrétaire" in t2, "tout en gardant ce qu'elle a écrit")
    pg.click("#fermer"); pg.wait_for_timeout(250)

    # ══ 2. LES VISITEURS, UNE PAGE ENTIÈRE ══════════════════════════
    h, t = doc("#imp-emarg", "#t-tenue")
    v("Feuille d’émargement — Visiteurs" in t,
      "LA FEUILLE DES VISITEURS A SON PROPRE TITRE")
    v('class="saut"' in h, "et commence sur une page neuve")
    v(h.count("A∴L∴G∴D∴G∴A∴D∴L∴U∴") == 2,
      "l'en-tête de l'Atelier y est repris : c'est une feuille à part",
      h.count("A∴L∴G∴D∴G∴A∴D∴L∴U∴"))
    apres = h.split('class="saut"')[1]
    # On compte DANS LE CORPS DU TABLEAU. « apres » porte aussi l'en-tete
    # de l'Atelier, qui est lui-meme un tableau : retrancher une seule
    # ligne en laissait passer deux, et le compte etait faux depuis le
    # debut. Il passait tant que le nombre etait large.
    # LE DERNIER tbody, non le premier : le navigateur en insere un dans
    # le tableau de l'en-tete aussi, et c'est celui-la qu'on attrapait.
    corps = apres.split("<tbody>")[-1].split("</tbody>")[0]
    lignes = corps.count("<tr>")
    # Treize, mesure prise : le doctype a fait passer le programme en mode
    # standard, ou la meme feuille occupe un peu plus de hauteur. Au-dela
    # de treize, l'emargement deborde sur une TROISIEME page qui ne porte
    # que quelques traits — une feuille perdue a chaque tenue. Le nombre
    # de lignes se plie a la page, non l'inverse.
    v(lignes >= 13, f"elle offre au moins treize lignes (elle en offre {lignes})", lignes)
    for col in ["Nom et prénom", "Grade", "Loge, Orient, Obédience", "Tuilé par", "Signature"]:
        v(col in apres, f"colonne « {col} »")
    v("après avoir été tuilé" in apres,
      "et elle rappelle que nul ne signe sans avoir été tuilé")
    v(corps.count('class="sig"') == lignes,
      "chaque ligne porte son trait de signature — autant de traits que de "
      "lignes, quel que soit leur nombre", (corps.count('class="sig"'), lignes))

    # ── CE QUI TOMBE SUR LE PAPIER ──────────────────────────────────
    # Une convocation en deux feuillets, c'est douze envois dont le
    # second ne porte qu'une signature et un adage. Et un contreseing
    # seul sur une troisième page est une feuille perdue. On compte
    # donc les pages, pour de bon.
    import re as _re
    def pages(bouton, onglet=None):
        if onglet: pg.click(onglet); pg.wait_for_timeout(400)
        pg.click(bouton); pg.wait_for_timeout(900)
        pdf = pg.pdf(format="A4",
                     margin={"top":"12mm","bottom":"12mm","left":"14mm","right":"14mm"},
                     print_background=True)
        pg.click("#fermer"); pg.wait_for_timeout(250)
        return len(_re.findall(rb'/Type\s*/Page[^s]', pdf))

    n = pages("#imp-convoc", "#t-convoc")
    v(n == 1, f"LA CONVOCATION TIENT SUR UNE SEULE PAGE (elle en fait {n})", n)

    # ── ET ELLE Y TIENT AVEC UN VRAI ORDRE DU JOUR ─────────────────
    # Dix points, dont quatre passent a la ligne : c'est l'ordre du jour
    # reel du 5 octobre. Sans serrage, le feuillet passait sur une
    # seconde page qui ne portait qu'un adage et une ligne de contact —
    # a cent envois, cent feuilles perdues.
    CHARGE = [("18:15","Convocation de tous les SS et FF Maitres de la loge (conseil des Maitres)"),
      ("19:30","Ouverture de la Tenue au premier degre d'Apprenti Oved"),
      ("19:45","Quelques mots de bienvenue du Venerable Maitre"),
      ("20:00","Cinq minutes de symbolisme — « L'initiation au Rite Brith Israel », par le SGC Mickael DARMON"),
      ("20:30","Impressions d'initiation de notre A Caroline A…"),
      ("21:40","Planche de notre F Pierre J… : le tapis de LOGE au BRITH ISRAEL"),
      ("22:00","Lecture de la lettre de demande d'affiliation du F Atteia Oved et vote pour approbation"),
      ("22:30","Cloture des travaux au degre Oved"),
      ("23:00","Agapes fraternelles — triangle 15 euros, inscription avant le 2 octobre"),
      ("19:15","Accueil sur les parvis des AA CC de la loge et visiteurs")]
    garde = pg.evaluate("() => JSON.stringify(E.odj)")
    pg.evaluate("(o) => { E.odj = o.map(x => ({h:x[0], t:x[1]})); garder(); dessiner(); }", CHARGE)
    pg.wait_for_timeout(600)
    n = pages("#imp-convoc", "#t-convoc")
    v(n == 1, f"ET AVEC DIX POINTS A L'ORDRE DU JOUR, ELLE Y TIENT ENCORE (elle en fait {n})", n)

    pg.click("#t-convoc"); pg.wait_for_timeout(400)
    pg.click("#imp-convoc"); pg.wait_for_timeout(800)
    z = float(pg.evaluate("() => document.getElementById('papier').style.zoom || 1"))
    v(0.78 <= z < 1, f"le feuillet a ete resserre, sans descendre sous 78 % ({z})", z)
    v(z >= 0.80, "et il reste lisible : on ne resserre qu'autant qu'il faut", z)
    pg.click("#fermer"); pg.wait_for_timeout(250)

    # ── LE MOT D'ACCUEIL OUVRE LE COURRIEL, ET LUI SEUL ────────────
    txt = pg.evaluate("() => convocationTexte()")
    v("Mon tr\u00e8s cher Fr\u00e8re" in txt,
      "LE COURRIEL S'OUVRE SUR UN MOT D'ACCUEIL", txt[:160])
    h2, t2 = doc("#imp-convoc", "#t-convoc")
    v("Mon tr\u00e8s cher Fr\u00e8re" not in t2,
      "MAIS LE FEUILLET NE LE PORTE PAS : l'en-tete y dit deja l'essentiel, "
      "et la page est comptee", t2[:160])

    pg.evaluate("(g) => { E.tenue.motAccueil = ''; E.odj = JSON.parse(g); garder(); dessiner(); }", garde)
    pg.wait_for_timeout(500)
    txt = pg.evaluate("() => convocationTexte()")
    v("Mes bien chers S\u0153urs et Fr\u00e8res" in txt,
      "laisse vide, la formule ordinaire revient", txt[:160])
    n = pages("#imp-emarg", "#t-tenue")
    v(n == 2, f"l'émargement fait deux pages : les membres, puis les "
              f"Visiteurs — et rien ne déborde sur une troisième (il en fait {n})", n)
    n = pages("#imp-carnet", "#t-visiteurs")
    v(n == 1, f"le carnet des visiteurs tient sur une page (il en fait {n})", n)

    # == LE MOT DE FIN, AU BAS DE LA CONVOCATION ====================
    # Il est gardé dans le registre de l'Atelier, jamais écrit dans le
    # programme : ce fichier est servi en clair sur le site, et
    # l'appartenance maçonnique d'une personne n'a pas à y figurer.
    # LA LIGNE EST ICI, ET ELLE N'EST PAS LA MIENNE. Le Souverain Grand
    # Commandeur a tranche : le prenom et l'INITIALE du nom peuvent
    # figurer au mot de fin — c'est la convention du Rite, celle que
    # l'annuaire emploie deja (« Nom (ou initial) »).
    #
    # Ce qui reste interdit dans ce fichier servi en clair : un NOM DE
    # FAMILLE entier, et une adresse de courriel personnelle. Les deux
    # ensemble designent quelqu'un ; une initiale, non.
    # LA LISTE DE GARDE NE PORTE PAS LES NOMS QU'ELLE GARDE. Ecrire
    # ici les noms des Sœurs et Freres dans un depot public, c'etait
    # publier la liste des Sœurs et Freres de l'Atelier — le garde-fou
    # faisait lui-meme la fuite qu'il devait empecher.
    #
    # On garde leurs EMPREINTES. On releve tous les mots en capitales
    # de la page, on les empreinte, et l'on compare : un nom qui s'y
    # glisserait serait reconnu sans avoir jamais ete ecrit ici.
    import hashlib, io, re as _re
    EMPREINTES = ['00fa6ed7d665', '07083d867cae', '0e116a9faf64', '1e3a6119ee11', '329ccd680d9b', '62aa42deefc5', '6555706078a9', '6c94d0e5823e', '890aa779b6ed', '935b7474a054', '9a722032ed9b', 'a1df48acdc6d', 'c14964440bfd', 'd07c7bea47f5', 'dd4054a74e88']
    # La page de réponse est servie au même titre que le programme, et
    # à qui n'a pas de compte : elle tombe sous la même garde.
    PUBLIC = PAGE + io.open("reponse.html", encoding="utf-8").read()
    mots = set(_re.findall(r"[A-ZÀ-Þ][A-ZÀ-Þ'\-]{3,}", PUBLIC))
    fuites = [m for m in mots
              if hashlib.sha256(m.encode()).hexdigest()[:12] in EMPREINTES]
    v(not fuites,
      "AUCUN NOM DE FAMILLE D'UN MEMBRE N'EST ECRIT DANS LE PROGRAMME", fuites)
    v(len(EMPREINTES) == 15, "et la garde porte bien sur quinze noms", len(EMPREINTES))
    motfin = pg.evaluate("E.tenue.motFin")
    v("@" not in motfin,
      "et le mot de fin ne porte aucune adresse de courriel personnelle", motfin)
    v(pg.evaluate("typeof E.tenue.motFin") == "string",
      "le mot de fin est un champ du registre", pg.evaluate("typeof E.tenue.motFin"))

    h, t = doc("#imp-convoc", "#t-convoc")
    v("enregistrer individuellement sur le site" in t,
      "LA CONVOCATION LE PORTE", t[-300:])
    v("notre Soeur Secretaire".replace("oe", "\u0153").replace("Secretaire",
      "Secr\u00e9taire") in t, "et nomme la charge", t[-300:])

    # on y ajoute un nom, comme le fera le Souverain Grand Commandeur
    pg.click("#t-convoc"); pg.wait_for_timeout(400)
    pg.evaluate("""() => { const c = document.getElementById('f-motFin');
      c.value = c.value.replace(/\\.$/, ' Une Soeur.');
      c.dispatchEvent(new Event('input', {bubbles:true})); }""")
    pg.wait_for_timeout(700)
    h, t = doc("#imp-convoc")
    v("Une Soeur" in t, "le nom ajouté s'imprime", t[-200:])
    txt = pg.evaluate("convocationTexte()")
    v("enregistrer individuellement sur le site" in txt and "Une Soeur" in txt,
      "et la convocation envoyée par courriel le porte aussi", txt[-300:])

    # avec le nom, la convocation doit TOUJOURS tenir sur une feuille :
    # c'est la forme qu'elle aura tous les mois.
    import re as _re0
    pg.click("#t-convoc"); pg.wait_for_timeout(400)
    pg.click("#imp-convoc"); pg.wait_for_timeout(900)
    _pdf = pg.pdf(format="A4", margin={"top":"12mm","bottom":"12mm",
                  "left":"14mm","right":"14mm"}, print_background=True)
    _n = len(_re0.findall(rb'/Type\s*/Page[^s]', _pdf))
    pg.click("#fermer"); pg.wait_for_timeout(250)
    v(_n == 1, f"ET ELLE TIENT ENCORE SUR UNE PAGE, mot de fin compris "
               f"(elle en fait {_n})", _n)

    # vide, il ne s'imprime pas
    pg.click("#t-convoc"); pg.wait_for_timeout(400)
    pg.evaluate("""() => { const c = document.getElementById('f-motFin');
      c.value = ''; c.dispatchEvent(new Event('input', {bubbles:true})); }""")
    pg.wait_for_timeout(700)
    h, t = doc("#imp-convoc")
    v("enregistrer individuellement" not in t,
      "laissé vide, il ne s'imprime pas du tout")

    # et on le remet, pour la mesure des pages qui suit
    pg.click("#t-convoc"); pg.wait_for_timeout(400)
    pg.evaluate("""() => { const c = document.getElementById('f-motFin');
      c.value = 'Mes Soeurs, mes Freres. Merci de bien vouloir vous enregistrer '
              + 'individuellement sur le site et, en cas de doute, de contacter '
              + 'notre Soeur Secretaire Une Soeur Quelconque.';
      c.dispatchEvent(new Event('input', {bubbles:true})); }""")
    pg.wait_for_timeout(700)

    # ══ 3. LE POINT DU TEMPLE ═══════════════════════════════════════
    v(pg.evaluate("E.tenue.lieuGps") in ("", None),
      "aucun point GPS n'est inventé au départ", pg.evaluate("E.tenue.lieuGps"))
    h, t = doc("#imp-convoc", "#t-convoc")
    v("ouvrir dans un plan" in t, "sans point relevé, la convocation mène à l'adresse")
    lien = re.search(r'href="([^"]*maps[^"]*)"', h)
    v(bool(lien) and "Ventabren" in lien.group(1).replace("%20", " ").replace("+", " ")
      or bool(lien) and "VENTABREN" in lien.group(1),
      "et ce lien porte bien l'adresse du Temple", lien.group(1) if lien else None)
    v("Point GPS" not in t, "et ne prétend pas donner un point qu'on n'a pas")

    # on relève le point
    pg.click("#t-convoc"); pg.wait_for_timeout(400)
    pg.evaluate("""() => { const c = document.getElementById('f-lieuGps');
      c.value = '43.512340, 5.398760';
      c.dispatchEvent(new Event('input', {bubbles:true})); }""")
    pg.wait_for_timeout(600)
    v(pg.evaluate("E.tenue.lieuGps") == "43.512340, 5.398760",
      "le point relevé s'enregistre", pg.evaluate("E.tenue.lieuGps"))
    h, t = doc("#imp-convoc")
    v("Point GPS 43.512340, 5.398760" in t,
      "LA CONVOCATION PORTE ALORS LE POINT", t[:400])
    lien = re.search(r'href="([^"]*maps[^"]*)"', h)
    v(bool(lien) and "43.512340" in lien.group(1),
      "et le lien y mène exactement", lien.group(1) if lien else None)

    # la convocation envoyée par courriel le porte aussi
    txt = pg.evaluate("convocationTexte()")
    v("Point GPS : 43.512340, 5.398760" in txt,
      "la convocation par courriel le porte également", txt[:300])
    v("maps" in txt, "avec le lien")

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  {len(ko)} échec(s)" if ko else "\n  tout passe")
