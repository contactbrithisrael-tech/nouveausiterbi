# L'ÉPREUVE DE LA PAGE EN ACCÈS LIBRE
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8806 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-loges-amies.py
#
# CE QU'ON ÉPROUVE. Les deux formulaires d'Atelier vivaient DERRIÈRE
# le tuilage de l'Espace Membres, où ils ne servaient à rien : une
# Loge qu'on ne connaît pas encore ne peut pas franchir un tuilage
# pour se faire connaître. Ils sont désormais sur une page ouverte.
#
# Ouvrir une page, c'est ouvrir une porte. On éprouve donc les deux
# côtés : que la Loge inconnue arrive jusqu'au carnet de la
# Secrétaire SANS RIEN FRANCHIR, et que cette page ouverte ne donne
# accès à rien d'autre.
from playwright.sync_api import sync_playwright
import os, json, urllib.request

U = os.environ.get("RBI_URL", "http://127.0.0.1:8806/")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []

def v(c, n, d=''):
    print(f"  {'✓' if c else '✗'} {n}{'' if c else '  <- ' + str(d)[:260]}")
    if not c: ko.append(n)

def table(nom):
    with urllib.request.urlopen(U + "__table?nom=" + nom) as r:
        return json.load(r)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    cL = b.new_context(); L = cL.new_page()
    eL = []; L.on("pageerror", lambda e: eL.append(str(e)))

    # ══ 1. AUCUN SEUIL À FRANCHIR ═══════════════════════════════════
    L.goto(U + "loges-amies.html"); L.wait_for_timeout(700)
    v(L.locator("#form-loge").is_visible(),
      "LA PAGE S'OUVRE SUR SON FORMULAIRE : ni tuilage, ni mot de passe, "
      "ni compte à créer")
    v(L.locator(".porte").count() == 0,
      "aucune porte n'est posée devant", L.locator(".porte").count())
    v(L.locator("#ong-conv").is_visible(),
      "et le second formulaire est à un onglet de là")

    # ══ 2. OUVERTE AU DÉPÔT N'EST PAS OUVERTE À LA LECTURE ══════════
    # C'est le point qui décide si cette page pouvait être ouverte.
    lire = L.evaluate("""async () => {
      const a = await (await fetch('/api/annuaire')).json();
      const e = await (await fetch('/api/etat')).json();
      return { annuaire: a, etat: e }; }""")
    v(lire["annuaire"].get("erreur") == "non_connecte",
      "DÉPOSER N'EST PAS RELEVER : la boîte aux lettres ne se lit pas d'ici",
      lire["annuaire"])
    v(lire["etat"].get("erreur") == "non_connecte",
      "ET LE REGISTRE DE L'ATELIER RESTE FERMÉ : la page ouverte n'ouvre rien d'autre",
      lire["etat"])
    source = L.content()
    v(CLE not in source and "secretariat@epreuve.test" not in source,
      "la page ne porte ni clé ni adresse de l'Atelier")

    # ══ 3. UNE LOGE INCONNUE S'INSCRIT ══════════════════════════════
    for champ, valeur in (("l-nom", "La Pierre Cubique"), ("l-num", "77"),
                          ("l-or", "Avignon"), ("l-ob", "GLDF"),
                          ("l-ri", "REAA"), ("l-te", "Temple Salomon"),
                          ("l-ad", "12 rue des Teinturiers"),
                          ("l-cp", "84000"), ("l-vi", "Avignon"),
                          ("l-cn", "Esther L."),
                          ("l-ce", "secretariat@pierre-cubique.test"),
                          ("l-ct", "04 90 00 00 00")):
        L.fill("#" + champ, valeur)
    L.click("#form-loge button[type=submit]"); L.wait_for_timeout(1500)
    v(L.locator("#msg-loge").is_visible(),
      "l'inscription est confirmée", L.inner_text("#ennui-loge") if
      L.locator("#ennui-loge").is_visible() else "(aucun ennui affiché)")
    v(not L.locator("#form-loge").is_visible(),
      "et le formulaire se retire : on ne s'inscrit pas deux fois par inadvertance")
    v(not eL, "aucune erreur JavaScript", eL)

    recues = table("annuaire")
    depot = [json.loads(r["donnees"]) for r in recues]
    laLoge = [d for d in depot if d.get("loge_nom") == "La Pierre Cubique"]
    v(len(laLoge) == 1, "la fiche est au registre", [d.get("loge_nom") for d in depot])
    if laLoge:
        v(laLoge[0].get("type") == "loge", "rangée comme une Loge", laLoge[0])
        v(laLoge[0].get("contact_email") == "secretariat@pierre-cubique.test",
          "avec l'adresse de son secrétariat", laLoge[0])
    v(any(r["source"] == "loges-amies" for r in recues),
      "ET LA SECRÉTAIRE SAURA D'OÙ ELLE VIENT : la source est notée",
      [r["source"] for r in recues])

    # ══ 4. ET DÉPOSE SA CONVOCATION ═════════════════════════════════
    L.goto(U + "loges-amies.html#convocation"); L.wait_for_timeout(700)
    v(L.locator("#sec-conv").is_visible(),
      "l'adresse partagée mène directement au bon formulaire")
    for champ, valeur in (("c-nom", "La Pierre Cubique"), ("c-num", "77"),
                          ("c-ce", "secretariat@pierre-cubique.test"),
                          ("c-da", "2027-03-21"), ("c-he", "19:30"),
                          ("c-ob", "Tenue d equinoxe"),
                          ("c-li", "Temple Salomon"),
                          ("c-fe", "https://pierre-cubique.test/planche.pdf"),
                          ("c-od", "Lecture d une planche")):
        L.fill("#" + champ, valeur)
    L.select_option("#c-de", "2")
    L.click("#form-conv button[type=submit]"); L.wait_for_timeout(1500)
    v(L.locator("#msg-conv").is_visible(), "le dépôt est confirmé",
      L.inner_text("#ennui-conv") if L.locator("#ennui-conv").is_visible() else "")
    v(not eL, "toujours aucune erreur JavaScript", eL)

    # ══ 5. LA SECRÉTAIRE OUVRE SON ÉCRAN ════════════════════════════
    # Personne n'a ouvert de courriel, personne n'a recopié quoi que
    # ce soit : c'est le seul but de toute cette chaîne.
    cM = b.new_context(); M = cM.new_page()
    eM = []; M.on("pageerror", lambda e: eM.append(str(e)))
    M.on("dialog", lambda d: d.accept())
    M.goto(U); M.wait_for_timeout(900)
    M.fill("#porte-mdp", CLE); M.click("#porte-form button[type=submit]")
    M.wait_for_timeout(2600)

    amie = M.evaluate(
        "(E.amies||[]).find(x => (x.nom||'').indexOf('Pierre Cubique') >= 0) || null")
    v(amie is not None,
      "LA LOGE INCONNUE EST AU CARNET DES LOGES AMIES, sans avoir rien franchi",
      M.evaluate("(E.amies||[]).map(x=>x.nom)"))
    if amie:
        v(amie.get("nom") == "La Pierre Cubique n°77",
          "avec son numéro, pour ne pas la confondre avec une homonyme",
          amie.get("nom"))
        v(amie.get("contactEmail") == "secretariat@pierre-cubique.test",
          "et l'adresse à qui écrire", amie.get("contactEmail"))
    v(M.evaluate("!(E.visiteurs||[]).some(x => (x.nom||'').indexOf('Cubique')>=0)"),
      "une Loge n'entre pas au carnet des Visiteurs : elle n'est jamais venue")
    v(M.evaluate("prochainesVisites().some(x => x.c.date === '2027-03-21')"),
      "ET SA TENUE EST À L'AGENDA DES VISITES",
      M.evaluate("prochainesVisites().map(x=>x.c.date)"))

    # ══ 6. UNE ERREUR DE SAISIE SE DIT, ELLE NE SE PERD PAS ═════════
    # « sarah@intranet » passe la vérification du navigateur et non
    # celle du serveur. Sans message, l'Atelier croirait être inscrit.
    L.goto(U + "loges-amies.html"); L.wait_for_timeout(700)
    L.fill("#l-nom", "La Fausse Adresse")
    L.fill("#l-ce", "sarah@intranet")
    L.click("#form-loge button[type=submit]"); L.wait_for_timeout(1200)
    v(not L.locator("#msg-loge").is_visible(),
      "UN DÉPÔT REFUSÉ N'EST JAMAIS CONFIRMÉ")
    v(L.locator("#ennui-loge").is_visible(), "l'ennui est dit")
    v("courriel" in L.inner_text("#ennui-loge").lower(),
      "et il dit QUEL champ reprendre", L.inner_text("#ennui-loge")[:200])
    v(L.locator("#form-loge").is_visible(),
      "le formulaire reste ouvert, avec ce qui a déjà été saisi")
    v(L.input_value("#l-nom") == "La Fausse Adresse",
      "et la saisie n'est pas perdue", L.input_value("#l-nom"))

    # ══ 7. LE LEURRE ════════════════════════════════════════════════
    L.goto(U + "loges-amies.html"); L.wait_for_timeout(700)
    # « is_visible » de Playwright dit qu'il est rendu, ce qui est vrai :
    # le leurre EST dans la page, sinon un automate ne le trouverait pas.
    # Ce qu'il faut mesurer, c'est qu'aucun œil ne le rencontre — il est
    # jeté hors de la page, à gauche.
    boite = L.evaluate("() => { const r = document.getElementById('l-an')"
                       ".getBoundingClientRect(); return { x: r.x, d: r.right }; }")
    v(boite["d"] < 0,
      "le champ-leurre est hors de la page : aucun œil ne le rencontre", boite)
    v(L.evaluate("() => document.getElementById('l-an').closest('[aria-hidden]')"
                 " !== null"),
      "et il est tu aux lecteurs d'écran")
    v(L.get_attribute("#l-an", "tabindex") == "-1",
      "ne s'atteint pas au clavier", L.get_attribute("#l-an", "tabindex"))
    avant = len(table("annuaire"))
    L.fill("#l-nom", "Loge Du Robot")
    L.fill("#l-ce", "robot@exemple.test")
    L.evaluate("document.getElementById('l-an').value = 'http://spam.test'")
    L.click("#form-loge button[type=submit]"); L.wait_for_timeout(1200)
    v(not L.locator("#msg-loge").is_visible(),
      "UNE MAIN QUI REMPLIT LE LEURRE N'EST PAS CONFIRMÉE")
    v(len(table("annuaire")) == avant,
      "et rien n'entre au registre", len(table("annuaire")) - avant)
    v(L.locator("#ennui-loge").is_visible() and
      "courriel" in L.inner_text("#ennui-loge").lower(),
      "MAIS LE REPLI PAR COURRIEL EST OFFERT : si le leurre se trompait, "
      "l'Atelier aurait toujours une route", L.inner_text("#ennui-loge")[:200])
    lien = L.get_attribute("#ennui-loge a", "href") or ""
    v(lien.startswith("mailto:"), "le repli ouvre bien la messagerie", lien[:80])
    v("loge_annexe" not in lien,
      "et le leurre ne se recopie pas dans le courriel", lien[:200])

    # ══ 8. LE PLAFOND HORAIRE ═══════════════════════════════════════
    # Le plafond des 300 en attente protégeait la base, non l'Atelier :
    # un robot les remplissait en une minute, et les Loges suivantes
    # étaient refusées jusqu'à ce qu'un humain relève la boîte. Le
    # plafond horaire se rouvre tout seul.
    def deposer(n):
        return L.evaluate("""async (n) => { const r = await fetch('/api/annuaire',
          { method:'POST', headers:{'content-type':'application/json'},
            body: JSON.stringify({ type:'loge', loge_nom:'Arrosage ' + n,
              contact_email:'a' + n + '@exemple.test' }) });
          return { s: r.status, c: await r.json() }; }""", n)

    dernier = None
    for i in range(60):
        dernier = deposer(i)
        if dernier["s"] != 200: break
    v(dernier and dernier["s"] == 429 and dernier["c"].get("erreur") == "trop_vite",
      "L'ARROSAGE EST ARRÊTÉ AVANT D'AVOIR REMPLI LA FILE", dernier)
    total = len(table("annuaire"))
    v(total < 300,
      "et la file des 300 places n'est pas entamée : elle attendrait un humain, "
      "le plafond horaire se rouvre seul", total)

    # et la page le dit à qui tombe dessus, au lieu de se taire
    L.goto(U + "loges-amies.html"); L.wait_for_timeout(700)
    L.fill("#l-nom", "La Loge Malchanceuse")
    L.fill("#l-ce", "malchance@exemple.test")
    L.click("#form-loge button[type=submit]"); L.wait_for_timeout(1200)
    v(not L.locator("#msg-loge").is_visible(),
      "une Loge refusée par le plafond n'est pas confirmée non plus")
    v(L.locator("#ennui-loge").is_visible() and
      (L.get_attribute("#ennui-loge a", "href") or "").startswith("mailto:"),
      "ET ON LUI OUVRE LA ROUTE DU COURRIEL : le plafond ne lui fait pas "
      "perdre son inscription", L.inner_text("#ennui-loge")[:200])

    v(not eL, "aucune erreur JavaScript sur la page ouverte, du début à la fin", eL)
    v(not eM, "aucune erreur JavaScript à l'écran de la Secrétaire", eM)
    b.close()

print()
print("ÉPREUVE DE LA PAGE EN ACCÈS LIBRE :", "TOUT PASSE" if not ko else str(len(ko)) + " ÉCHEC(S)")
for x in ko: print("  ✗", x)
raise SystemExit(1 if ko else 0)
