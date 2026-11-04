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
    v(pg.locator("button[data-agp-paye='m9301']").inner_text().strip().endswith("Payé") and "Pas" not in pg.locator("button[data-agp-paye='m9301']").inner_text(),
      "le membre est payé d'office")
    v("Pas payé" in pg.locator("button[data-agp-paye='v1']").inner_text(), "le visiteur est pas payé d'abord")
    pg.click("button[data-agp-paye='v1']"); pg.wait_for_timeout(300)
    v("Pas" not in pg.locator("button[data-agp-paye='v1']").inner_text(), "un clic le marque payé")
    pg.click("button[data-agp-paye='m9301']"); pg.wait_for_timeout(300)
    v("Pas payé" in pg.locator("button[data-agp-paye='m9301']").inner_text(), "un membre peut être marqué pas payé")
    pg.evaluate("() => { courante='tenue'; dessiner(); }"); pg.wait_for_timeout(300)
    v(not err, "aucune erreur JavaScript", err)
    b.close()
print("\n  tout passe" if not ko else f"\n  {len(ko)} échec(s)")
