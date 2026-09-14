# L'ÉPREUVE DU MOT DE PASSE PERSONNEL
#   node loge/serveur/faux-page.mjs > /tmp/page-epreuve.html
#   export RBI_PAGE=/tmp/page-epreuve.html
#   RBI_PORT=8790 node loge/serveur/faux-serveur.mjs &
#   RBI_PORT=8791 RBI_SANS_COMPTES=1 node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-mdp.py
#
# CE QUI EST EN JEU. Les deux premiers mots de passe ont été choisis
# par un tiers, dits dans un courriel, et écrits une soirée durant
# dans un fichier d'épreuve d'un dépôt public. Aucun des trois ne
# s'efface. Ils doivent donc pouvoir être remplacés — ET LE
# REMPLACEMENT DOIT VALOIR QUELQUE CHOSE.
#
# Or la page porte encore, en clair, l'empreinte des mots de passe du
# premier jour, et le repli de la porte les accepte quand le serveur
# refuse. Sans précaution, l'ancien mot de passe rouvrirait toujours :
# le changement serait une décoration. C'est le cœur de cette épreuve.
from playwright.sync_api import sync_playwright
import os

AVEC = os.environ.get("RBI_URL_AVEC", "http://127.0.0.1:8790/")
SANS = os.environ.get("RBI_URL_SANS", "http://127.0.0.1:8791/")
CLE  = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
NEUF = "le cèdre du Liban en hiver"
ko = []

def v(c, n, d=''):
    print(f"  {'✓' if c else '✗'} {n}{'' if c else '  <- ' + str(d)[:220]}")
    if not c: ko.append(n)

def entrer(pg, url, mdp, attente=2000):
    pg.goto(url); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", mdp); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(attente)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context(); pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    # ══ AVANT : la page ne doit PAS doubler le serveur ══════════════
    # Le mot de passe de la page est le même que celui du serveur ici,
    # donc on éprouve l'inverse : un mot de passe QUE SEULE LA PAGE
    # connaîtrait n'existe pas. On éprouve la règle à l'étape 3.

    entrer(pg, AVEC, CLE)
    v(pg.locator("#appli").is_visible(), "la Secrétaire entre avec le mot de passe reçu")
    v(pg.evaluate("SERVEUR.actif") is True, "par le serveur")
    v(not pg.locator("#ouvrir-mdp").is_hidden(),
      "LE BOUTON « MON MOT DE PASSE » EST LÀ")

    # ══ 1. LES REFUS SONT DITS, PAS DEVINÉS ════════════════════════
    pg.click("#ouvrir-mdp"); pg.wait_for_timeout(500)
    v(pg.locator("#mdp-ecran").is_visible(), "l'écran du changement s'ouvre")

    def essayer(ancien, neuf, neuf2, attente=1600):
        pg.fill("#mdp-ancien", ancien); pg.fill("#mdp-neuf", neuf)
        pg.fill("#mdp-neuf2", neuf2)
        pg.click("#mdp-form button[type=submit]"); pg.wait_for_timeout(attente)
        e = pg.locator("#mdp-erreur")
        return e.inner_text() if e.count() and not e.is_hidden() else ''

    v("diffèrent" in essayer(CLE, NEUF, NEUF + "x", 400),
      "deux nouveaux mots différents : on le dit avant même d'écrire au serveur")
    v("dix caractères" in essayer(CLE, "court", "court", 400),
      "un mot trop court est refusé, et la raison est donnée")
    v("actuel n’est pas le bon" in essayer("pasbon", NEUF, NEUF),
      "un mot de passe actuel faux est refusé PAR LE SERVEUR",
      pg.locator("#mdp-erreur").inner_text())

    # le serveur refuse aussi de lui-même, sans l'aide de la page
    r = pg.evaluate("""async () => {
      const x = await fetch('/api/mdp', { method:'POST', credentials:'same-origin',
        headers:{'content-type':'application/json'},
        body: JSON.stringify({ ancien:'""" + CLE + """', nouveau:'court' }) });
      return { s: x.status, c: await x.json() }; }""")
    v(r["s"] == 400 and r["c"]["erreur"] == "trop_court",
      "le serveur ne se fie pas à la page : il vérifie la longueur lui-même", r)

    # ══ 2. LE CHANGEMENT ═══════════════════════════════════════════
    v(essayer(CLE, NEUF, NEUF) == "", "le changement est accepté",
      pg.locator("#mdp-erreur").inner_text())
    v(pg.locator("#mdp-ecran").is_hidden(), "et l'écran se referme")

    # ══ 3. L'ANCIEN MOT DE PASSE NE DOIT PLUS RIEN OUVRIR ══════════
    c2 = b.new_context(); q = c2.new_page()
    e2 = []; q.on("pageerror", lambda e: e2.append(str(e)))
    q.on("dialog", lambda d: d.accept())
    entrer(q, AVEC, CLE, 2500)
    v(not q.locator("#appli").is_visible(),
      "L'ANCIEN MOT DE PASSE N'OUVRE PLUS RIEN — "
      "l'empreinte restée dans la page ne le sauve pas")
    v(q.evaluate("SERVEUR.repli") is False,
      "et la page ne se replie pas sur elle-même : le serveur sait reconnaître",
      q.evaluate("SERVEUR.repli"))
    v(q.locator("#porte-erreur").is_visible(), "le refus est dit")

    entrer(q, AVEC, NEUF, 2500)
    v(q.locator("#appli").is_visible(), "LE NOUVEAU MOT DE PASSE OUVRE")
    v(q.evaluate("SERVEUR.actif") is True, "par le serveur")
    v(q.evaluate("SERVEUR.nom") == "Sœur Secrétaire d’épreuve",
      "et c'est bien le même compte", q.evaluate("SERVEUR.nom"))

    # ══ 4. LE REPLI RESTE, LÀ OÙ IL SAUVE ══════════════════════════
    # Serveur sans aucun compte : il refuse tout le monde, son refus
    # n'apprend rien, et la page doit rouvrir.
    c3 = b.new_context(); z = c3.new_page()
    e3 = []; z.on("pageerror", lambda e: e3.append(str(e)))
    z.on("dialog", lambda d: d.accept())
    entrer(z, SANS, CLE, 2500)
    v(z.locator("#appli").is_visible(),
      "serveur sans aucun compte : on entre quand même, comme avant")
    v(z.evaluate("SERVEUR.repli") is True, "et le repli est annoncé")
    v(z.locator("#alerte-repli").count() == 1, "avec son bandeau")
    v(z.locator("#ouvrir-mdp").is_hidden(),
      "MAIS PAS LE BOUTON DU MOT DE PASSE : il n'y a aucun compte à changer")

    v(not errs and not e2 and not e3, "aucune erreur JavaScript", errs + e2 + e3)
    b.close()

print(f"\n  {len(ko)} échec(s)" if ko else "\n  tout passe")
