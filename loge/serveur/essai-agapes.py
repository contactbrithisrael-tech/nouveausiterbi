# L'EPREUVE DE L'ONGLET AGAPES (serveur d'épreuve, port 8815)
from playwright.sync_api import sync_playwright
import os
U = os.environ.get("RBI_URL", "http://127.0.0.1:8815/")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []
def v(c, n, d=''):
    print(f"  {'OK' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:200]}")
    if not c: ko.append(n)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_context().new_page()
    err = []; pg.on("pageerror", lambda e: err.append(str(e)))
    pg.goto(U); pg.wait_for_timeout(800)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(2500)
    pg.evaluate("""() => {
      E.membres.push({id:9301, prenoms:'Paul', nom:'MEMBRE', statut:'actif'},
                     {id:9302, prenoms:'Non', nom:'INSCRIT', statut:'actif'});
      E.presences[9301]='present'; E.agapes[9301]=true; E.presences[9302]='present';
      E.visiteurs.length = 0;
      E.visiteurs.push({id:1,prenom:'Chimon',nom:'EDOUT',grade:'Maître',loge:'GLTF',presentTenue:true,visites:[]},
                       {id:2,prenom:'Rien',nom:'AGAPES',grade:'Apprenti',presentTenue:true,visites:[]});
      E.visiteurs.push({id:3,prenom:'Annonce',nom:'VENUE',grade:'Compagnon',presentTenue:true,visites:[]});
      E.agapesVisiteurs = {1:true, 2:false}; E.reponsesAmis = {}; }""")
    v(pg.locator("#t-listeagapes").count() == 1, "l'onglet Agapes existe")
    pg.click("#t-listeagapes"); pg.wait_for_timeout(500)
    t = pg.inner_text("#v-listeagapes")
    v("MEMBRE" in t and "EDOUT" in t, "membre et visiteur inscrits y figurent")
    v("INSCRIT" not in t and "AGAPES Rien" not in t, "les non-inscrits n'y figurent pas", t)
    v("VENUE" in t and "À confirmer" in t, "un visiteur attendu, qui n'a pas dit s'il mange, y figure « à confirmer »", t)
    pg.evaluate("""() => { const d = E.tenue.date;
      E.visiteurs.push({id:4,prenom:'Futur',nom:'ANNONCE',grade:'Maître',presentTenue:false,visites:[],annonces:[{date:'2099-01-01'}]},
                       {id:5,prenom:'Ancien',nom:'PASSE',grade:'Maître',presentTenue:false,visites:[],annonces:[{date:'2001-01-01'}]});
      dessiner(); }""")
    t = pg.inner_text("#v-listeagapes")
    v("ANNONCE" in t, "un visiteur qui a annoncé sa venue figure sur la liste", t)
    v("Annoncés pour une autre date" in t and "PASSE" in t, "un visiteur annoncé pour une date passée est signalé en dessous")
    v(pg.locator("#v-listeagapes table").count() == 1, "une seule liste, pas trois tableaux")
    v("capitation" in t and pg.locator("button[data-agp-paye='membre paul']").count() == 0,
      "un membre est payé d'office, sans bouton (agapes comprises dans la capitation)")
    v("Pas payé" in pg.locator("button[data-agp-paye='chimon edout']").inner_text(), "le visiteur est pas payé d'abord")
    pg.click("button[data-agp-paye='chimon edout']"); pg.wait_for_timeout(600)
    v("Pas" not in pg.locator("button[data-agp-paye='chimon edout']").inner_text(), "un clic le marque payé")
    srv = pg.evaluate("async () => await (await fetch('/api/agapes')).json()")
    v("chimon edout" in srv.get("payes", []), "le serveur l'a retenu (tables du Maître des banquets)", srv)
    # le Maître des banquets coche un autre visiteur et ajoute un nom : le Secrétariat le voit
    pg.evaluate("""async () => { await fetch('/api/agapes', {method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({marquer:{cle:'chimon edout', paye:false}}) });
      await fetch('/api/agapes', {method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({ajouter:{nom:'Zacharie AJOUTE', qualite:'visiteur'}}) }); }""")
    pg.evaluate("releverAgapes()"); pg.wait_for_timeout(800)
    t2 = pg.inner_text("#v-listeagapes")
    v("AJOUTE" in t2 and "Maître des banquets" in t2, "un nom ajouté par le Maître des banquets figure au Secrétariat")
    v("Pas payé" in pg.locator("button[data-agp-paye='chimon edout']").inner_text(),
      "le paiement décoché là-bas est décoché ici")
    # le Secrétariat → le Maître des banquets
    pg.evaluate("garder()"); pg.wait_for_timeout(2500)
    ban = pg.evaluate("""async () => { const r = await fetch('/api/banquets', {method:'POST',
        headers:{'content-type':'application/json'}, body: JSON.stringify({courriel:'a@b.test'}) });
      return { s: r.status, c: await r.json() }; }""")
    if ban["s"] == 200:
        noms = [g["nom"] for g in ban["c"].get("gens", [])]
        v(any("EDOUT" in n.upper() for n in noms) and any("MEMBRE" in n.upper() for n in noms),
          "les inscrits du Secrétariat sont sur la liste du Maître des banquets", noms)
    else:
        print("  (banquets : accès refusé en épreuve, statut", ban["s"], ")")
    pg.evaluate("() => { courante='tenue'; dessiner(); }"); pg.wait_for_timeout(300)
    v(not err, "aucune erreur JavaScript", err)
    b.close()
print("\n  tout passe" if not ko else f"\n  {len(ko)} échec(s)")
