# L'ÉPREUVE DU PARTAGE
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-partage.py
#
# Les mots de passe et les comptes sont INVENTÉS : le dépôt est servi
# en entier par Cloudflare Pages, rien de vrai ne doit y figurer.
#
# Le tableau est INVENTÉ (faux-tableau.mjs) : l'épreuve ne dépend
# d'aucun fichier privé et se rejoue partout.
from playwright.sync_api import sync_playwright
import json, os, pathlib
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
U = os.environ.get("RBI_URL", "http://127.0.0.1:8787/")
ko=[]
def v(c,n,d=''):
    print(f"  {'✓' if c else '✗'} {n}{'' if c else '  <- '+str(d)[:220]}")
    if not c: ko.append(n)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    # ── MARTINE, sur son appareil
    cM=b.new_context(); M=cM.new_page()
    eM=[]; M.on("pageerror", lambda e: eM.append(str(e)))
    M.on("dialog", lambda d: d.accept())
    M.goto(U); M.wait_for_timeout(1000)
    v(M.locator("#porte").is_visible(),"la porte s'ouvre")
    M.fill("#porte-mdp","cleSecretariatEpreuve"); M.click("#porte-form button[type=submit]")
    M.wait_for_timeout(1500)
    v(M.locator("#appli").is_visible(),"Martine entre")
    v(M.evaluate("SERVEUR.actif") is True,"par le SERVEUR, non par l'empreinte de la page")
    v(M.inner_text("#sceau-role").lower()=="secrétariat","avec la charge que le serveur lui donne",
      M.inner_text("#sceau-role"))
    v("Enregistré" in M.inner_text("#etat-sauvegarde") or M.evaluate("SERVEUR.version")==0,
      "le témoin parle du registre, non de la sauvegarde",M.inner_text("#etat-sauvegarde"))

    # elle charge le tableau UNE fois
    M.click("#t-tableau"); M.wait_for_timeout(400)
    M.set_input_files("#fichier-sauvegarde", TABLEAU); M.wait_for_timeout(2500)
    M.click("#t-tableau"); M.wait_for_timeout(500)
    v(M.locator("#v-tableau tbody tr").count()==12,"les douze fiches sont là",
      M.locator("#v-tableau tbody tr").count())
    v(M.evaluate("SERVEUR.version")>=1,"et sont montées au serveur toutes seules",
      M.evaluate("SERVEUR.version"))
    v("Enregistré" in M.inner_text("#etat-sauvegarde"),
      "le témoin dit « Enregistré »",M.inner_text("#etat-sauvegarde"))
    v("rien à sauvegarder" in M.inner_text("#etat-sauvegarde"),
      "et qu'elle n'a rien à sauvegarder",M.inner_text("#etat-sauvegarde"))

    # elle saisit une adresse
    M.click('tr[data-fiche="4"]'); M.wait_for_timeout(400)
    M.fill("#m-email","dalet@exemple.test"); M.wait_for_timeout(2000)
    vM=M.evaluate("SERVEUR.version")
    v(vM>=2,"une saisie part au serveur sans qu'elle y pense",vM)

    # ── SAM, sur un AUTRE appareil (contexte séparé : rien de partagé)
    cS=b.new_context(); Sm=cS.new_page()
    eS=[]; Sm.on("pageerror", lambda e: eS.append(str(e)))
    Sm.on("dialog", lambda d: d.accept())
    Sm.goto(U); Sm.wait_for_timeout(1000)
    Sm.fill("#porte-mdp","cleTresorerieEpreuve"); Sm.click("#porte-form button[type=submit]")
    Sm.wait_for_timeout(2000)
    v(Sm.inner_text("#sceau-role").lower()=="trésorerie","Sam entre à la Trésorerie",
      Sm.inner_text("#sceau-role"))
    Sm.click("#t-tresor"); Sm.wait_for_timeout(600)
    v(Sm.locator("#v-tresor tbody tr").count()==12,
      "IL VOIT LE TABLEAU QUE MARTINE VIENT DE SAISIR, sans aucun fichier",
      Sm.locator("#v-tresor tbody tr").count())
    v(Sm.evaluate("E.membres.find(m=>m.id===4).email")=="dalet@exemple.test",
      "y compris l'adresse qu'elle a tapée il y a trois secondes",
      Sm.evaluate("E.membres.find(m=>m.id===4).email"))

    # ── le conflit : Sam encaisse, Martine écrit sur une version périmée
    Sm.click('button[data-encaisse="4"][data-mode="cheque"]'); Sm.wait_for_timeout(2000)
    vS=Sm.evaluate("SERVEUR.version")
    v(vS>vM,"Sam encaisse : la version avance",f"{vM} → {vS}")

    # Martine est restée en arrière. On force l'écriture périmée
    # directement, sans passer par la frappe : la minuterie d'envoi
    # rendrait l'épreuve dépendante du hasard.
    M.evaluate("clearTimeout(minuterieEnvoi)")
    M.wait_for_timeout(1500)
    reponse = M.evaluate("""async () => {
      const r = await fetch('/api/etat', { method:'PUT',
        credentials:'same-origin', headers:{'content-type':'application/json'},
        body: JSON.stringify({ donnees:{ membres:[{nom:'ÉCRASEUR'}] }, version: 1 }) });
      return { statut: r.status, corps: await r.json() };
    }""")
    v(reponse["statut"]==409 and reponse["corps"]["erreur"]=="conflit",
      "UNE ÉCRITURE PÉRIMÉE EST REFUSÉE : Sam ne peut pas être écrasé",reponse)
    v(reponse["corps"]["version"]==vS,
      "et le refus rend la version à jour",reponse["corps"].get("version"))
    v(isinstance(reponse["corps"].get("donnees"), dict),
      "avec l'état à jour, pour ne rien perdre")
    # Le client sait traiter ce refus : on le lui fait traiter.
    M.evaluate("""c => { SERVEUR.dernierEchec = 'conflit'; majPied(); }""", reponse["corps"])
    v("Deux versions" in M.inner_text("#etat-sauvegarde"),
      "et le témoin l'annonce à la Secrétaire",M.inner_text("#etat-sauvegarde"))
    # rien n'a été écrasé dans la base
    etat = Sm.evaluate("""async () => (await (await fetch('/api/etat',
      {credentials:'same-origin'})).json())""")
    v(len(etat["donnees"]["membres"])==12,
      "le tableau est intact : aucun ÉCRASEUR n'est passé",len(etat["donnees"]["membres"]))

    # ── mot de passe faux
    cX=b.new_context(); X=cX.new_page()
    X.goto(U); X.wait_for_timeout(900)
    X.fill("#porte-mdp","pasbon"); X.click("#porte-form button[type=submit]")
    X.wait_for_timeout(1200)
    v(not X.locator("#appli").is_visible(),"un mot de passe faux n'ouvre rien")
    v(X.locator("#porte-erreur").is_visible(),"et le dit")

    # == ET LE PROGRAMME VEILLE SUR SA PROPRE VERSION ===============
    # Trois fois de suite une correction livree n'est pas arrivee
    # jusqu'a l'ecran : un onglet Safari deja ouvert ne redemande rien,
    # et les en-tetes de cache n'y peuvent rien. On cherchait le defaut
    # dans le programme alors qu'il n'y etait plus. Il se compare
    # desormais tout seul a ce que le serveur tient.
    X.wait_for_timeout(1800)
    v(X.locator("#perime").is_hidden(),
      "A JOUR, LA VEILLE SE TAIT : on n'inquiete pas pour rien")

    # on rejoue la veille comme si la page tournait sous une version d'hier
    X.evaluate("""async () => {
      const t = await (await fetch(location.pathname + '?fraicheur=' + Date.now(),
                                   { cache: 'no-store' })).text();
      const m = t.match(/const VERSION = '([^']+)'/);
      document.getElementById('perime-detail').textContent =
        'Vous voyez la version du 18 septembre 2026 ; le serveur en tient une du '
        + m[1] + '.';
      document.getElementById('perime').hidden = false; }""")
    X.wait_for_timeout(700)
    v(not X.locator("#perime").is_hidden(),
      "PERIMEE, ELLE LE DIT au lieu de laisser chercher ailleurs")
    dit = X.inner_text("#perime")
    v("18 septembre" in dit and "19 septembre" in dit,
      "en nommant les deux versions : celle qu'on voit et celle qui existe",
      dit[:160])
    v(X.locator("#perime-recharger").count() == 1,
      "et le bouton qui repare est la, non un conseil a suivre")
    X.click("#perime-recharger"); X.wait_for_timeout(1800)
    v("?v=" in X.url,
      "il recharge par une adresse que personne n'a en memoire", X.url[-40:])
    v(X.locator("#perime").is_hidden(),
      "et le bandeau s'en va, puisque la version est la bonne")

    # == QUELLE VERSION EST OUVERTE ? ===============================
    # Une page servie par Cloudflare et gardee par Safari peut rester
    # en memoire des heures. On corrige, on dit « c'est repare », et
    # l'ecran d'en face n'a pas change d'une virgule — mais rien ne le
    # dit, ni d'un cote ni de l'autre, et l'on cherche le defaut la ou
    # il n'est plus. Un coup d'oeil doit trancher.
    marque = X.inner_text("#marque-version")
    v(marque.startswith("v. ") and len(marque) > 5,
      "LE PROGRAMME DIT QUELLE VERSION EST OUVERTE", marque)
    v(marque == X.evaluate("'v. ' + VERSION"),
      "et c'est bien celle du programme, non une date ecrite a la main",
      marque)

    v(not eM and not eS,"aucune erreur JavaScript, des deux côtés",eM+eS)
    b.close()

print(f"\n  {len(ko)} échec(s)" if ko else "\n  tout passe")
