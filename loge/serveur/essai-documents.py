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

    def doc(bouton, onglet=None):
        if onglet: pg.click(onglet); pg.wait_for_timeout(400)
        pg.click(bouton); pg.wait_for_timeout(700)
        h = pg.inner_html("#papier"); t = pg.inner_text("#papier")
        pg.click("#fermer"); pg.wait_for_timeout(250)
        return h, t

    # ══ 1. LA QUALITÉ ET LE CONTRESEING ═════════════════════════════
    v(pg.evaluate("nomSgc()") == "Lamed ELOUL, 33°",
      "le Souverain Grand Commandeur est lu au Tableau, non écrit dans la page",
      pg.evaluate("nomSgc()"))
    v(pg.evaluate("souverainGrandCommandeur() && souverainGrandCommandeur().id") == 12,
      "c'est bien la fiche qui porte la qualité")

    for nom, bouton, onglet in [
        ("la convocation",          "#imp-convoc", "#t-convoc"),
        ("la feuille d'émargement", "#imp-emarg",  "#t-tenue"),
        ("la planche à tracer",     "#imp-planche", "#t-tenue"),
        ("le carnet des visiteurs", "#imp-carnet", "#t-visiteurs"),
    ]:
        h, t = doc(bouton, onglet)
        v("Vu et contresigné" in t, f"{nom} porte le contreseing", t[-200:])
        v("Souverain Grand Commandeur du Rite Brith Israël" in t,
          f"{nom} porte sa qualité en toutes lettres")
        v("Lamed ELOUL" in t, f"{nom} le nomme", t[-200:])
        v(t.count("Vu et contresigné") == 1,
          f"{nom} ne le porte qu'une fois", t.count("Vu et contresigné"))
        v('class="sig"' in h.split("Vu et contresigné")[-1],
          f"{nom} laisse une ligne pour la signature")

    # l'en-tête aussi
    h, t = doc("#imp-convoc", "#t-convoc")
    v("sous l’autorité du Souverain Grand Commandeur" in t,
      "l'en-tête de chaque document annonce son autorité")

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
    v("Vu et contresigné" not in enreg,
      "la planche enregistrée ne contient PAS le contreseing", enreg[-200:])
    pg.click("#fermer"); pg.wait_for_timeout(300)
    pg.click("#imp-planche"); pg.wait_for_timeout(700)
    t2 = pg.inner_text("#papier")
    v(t2.count("Vu et contresigné") == 1,
      "et rouvrir la planche ne le double pas", t2.count("Vu et contresigné"))
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
    lignes = apres.count("<tr>") - 1          # moins la ligne d'en-tête
    v(lignes >= 13, f"elle offre au moins treize lignes (elle en offre {lignes})", lignes)
    for col in ["Nom et prénom", "Grade", "Loge, Orient, Obédience", "Tuilé par", "Signature"]:
        v(col in apres, f"colonne « {col} »")
    v("après avoir été tuilé" in apres,
      "et elle rappelle que nul ne signe sans avoir été tuilé")
    v(apres.count('class="sig"') >= 13,
      "chaque ligne porte son trait de signature", apres.count('class="sig"'))

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
    n = pages("#imp-emarg", "#t-tenue")
    v(n == 2, f"l'émargement fait deux pages, pas trois : "
              f"le contreseing ne part pas seul sur une feuille (il en fait {n})", n)
    n = pages("#imp-carnet", "#t-visiteurs")
    v(n == 1, f"le carnet des visiteurs tient sur une page (il en fait {n})", n)

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
