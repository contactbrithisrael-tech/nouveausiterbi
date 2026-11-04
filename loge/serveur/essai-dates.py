# L'EPREUVE DES DATES TAPEES AU CLAVIER (naissance, initiation)
#   (même mise en place que essai-carnet.py ; serveur d'épreuve sur le port 8813)
from playwright.sync_api import sync_playwright
import os
U = os.environ.get("RBI_URL", "http://127.0.0.1:8813/")
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
    pg.evaluate("""() => { E.membres.push({id: 9001, prenoms:'Test', nom:'DATES', naissance:'',
      initiation:'', degre:null, qualite:'', du:0, regle:0, statut:'actif'});
      E.fiche = 9001; courante = 'fiche'; dessiner(); }""")
    pg.wait_for_timeout(500)
    v(pg.get_attribute("#m-naissance", "type") == "text",
      "le champ est un champ texte, pas un calendrier")
    pg.click("#m-naissance"); pg.keyboard.type("01021975"); pg.wait_for_timeout(300)
    v(pg.input_value("#m-naissance") == "01/02/1975", "les barres se posent seules",
      pg.input_value("#m-naissance"))
    v(pg.evaluate("E.membres.find(m=>m.id===9001).naissance") == "1975-02-01",
      "la fiche garde AAAA-MM-JJ", pg.evaluate("E.membres.find(m=>m.id===9001).naissance"))
    pg.keyboard.press("Tab"); pg.wait_for_timeout(400)
    v(pg.input_value("#m-naissance") == "01/02/1975", "la date reste après redessin")
    pg.fill("#m-naissance", "31/02/1975"); pg.keyboard.press("Tab"); pg.wait_for_timeout(300)
    v("non reconnue" in pg.inner_text("#a-naissance"), "une date impossible est signalée")
    v(pg.evaluate("E.membres.find(m=>m.id===9001).naissance") == "1975-02-01",
      "et la bonne date n'est pas écrasée par la mauvaise")
    pg.fill("#m-initiation", "5/3/2010"); pg.keyboard.press("Tab"); pg.wait_for_timeout(400)
    v(pg.evaluate("E.membres.find(m=>m.id===9001).initiation") == "2010-03-05",
      "5/3/2010 collé avec séparateurs est compris", pg.evaluate("E.membres.find(m=>m.id===9001).initiation"))
    pg.fill("#m-initiation", ""); pg.wait_for_timeout(200)
    v(pg.evaluate("E.membres.find(m=>m.id===9001).initiation") == "", "vider le champ efface la date")
    v(not err, "aucune erreur JavaScript", err)
    b.close()
print("\n  tout passe" if not ko else f"\n  {len(ko)} échec(s)")
