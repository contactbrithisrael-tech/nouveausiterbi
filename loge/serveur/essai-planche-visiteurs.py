# L'EPREUVE DE LA FEUILLE « VISITEURS VENUS » DE LA PLANCHE (serveur d'épreuve, port 8814)
from playwright.sync_api import sync_playwright
import os
U = os.environ.get("RBI_URL", "http://127.0.0.1:8814/")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []
def v(c, n, d=''):
    print(f"  {'OK' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:200]}")
    if not c: ko.append(n)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_context().new_page()
    err = []; pg.on("pageerror", lambda e: err.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(U); pg.wait_for_timeout(800)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(2500)
    pg.evaluate("""() => { E.visiteurs.length = 0;
      E.visiteurs.push({id:1,prenom:'Chimon',nom:'EDOUT',grade:'Maître',loge:'GLTF',orient:'Paris',obedience:'',presentTenue:true,visites:[]},
                       {id:2,prenom:'Absent',nom:'ABSENT',grade:'Apprenti',presentTenue:false,visites:[]}); }""")
    h = pg.evaluate("corpsPlanche()")
    v("Visiteurs venus" in h, "la feuille porte son titre")
    v(h.count("EDOUT") >= 2, "le visiteur coché présent y figure (liste + feuille)", h.count("EDOUT"))
    v("ABSENT" not in h, "le visiteur non coché n'y figure pas")
    v("Ont été présents à la tenue" in h and "Obédience" in h, "l'encart des présents est dans la planche")
    v("Sont présents les SS" not in h, "l'ancienne liste des membres n'est plus doublée")
    # excusés en permanence, y compris « en sommeil »
    pg.evaluate("""() => { E.membres.push(
      {id:9101, prenoms:'Philippe', nom:'NAKACHE', statut:'actif', excusePermanent:true, motifExcuse:''},
      {id:9102, prenoms:'Laurent', nom:'NOTARIANI', statut:'sommeil', excusePermanent:true, motifExcuse:'Réside au loin'}); }""")
    hx = pg.evaluate("corpsPlanche()")
    v("NAKACHE" in hx and "NOTARIANI" in hx, "les deux excusés permanents figurent à la planche")
    v("excusé en permanence" in hx, "avec la mention « excusé en permanence »")
    pg.evaluate("() => { E.membres.push({id:9201, prenoms:'Test', nom:'PRESENT', statut:'actif'}); E.presences[9201]='present'; }")
    v("R∴L∴ Bereshit n°00</td><td>l’Alliance</td>" in pg.evaluate("corpsPlanche()"),
      "les membres présents portent la Loge Bereshit et l'obédience l'Alliance")
    # visiteur sans obédience : une phrase avec son nom
    v("Est venu nous visiter le Maître Chimon EDOUT" in h,
      "sans obédience, « Est venu nous visiter le Maître » + son nom", h[h.find("EDOUT")-50:h.find("EDOUT")+250])
    # planche retouchée à la main : la feuille se refait quand même
    pg.evaluate("() => { E.plancheTexte = corpsPlanche().replace('Aucun.', 'Retouché'); }")
    pg.evaluate("() => { E.visiteurs.push({id:3,prenom:'Nouveau',nom:'COCHE',grade:'Compagnon',presentTenue:true,visites:[]}); }")
    h2 = pg.evaluate("plancheAvecAnnexe()")
    v("COCHE" in h2, "un visiteur coché après retouche apparaît dans la feuille")
    v(h2.count("data-annexe-visiteurs") == 1, "la feuille n'est pas dédoublée", h2.count("data-annexe-visiteurs"))
    pg.evaluate("() => { E.visiteurs.forEach(v => v.presentTenue = false); }")
    v("Aucun Visiteur" in pg.evaluate("plancheAvecAnnexe()"), "sans présent, la feuille le dit")
    v(not err, "aucune erreur JavaScript", err)
    b.close()
print("\n  tout passe" if not ko else f"\n  {len(ko)} échec(s)")
