# L'ÉPREUVE DE LA PORTE — ce qui arrive quand le serveur dit non
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   export RBI_PAGE=/tmp/page-epreuve.html
#   RBI_PORT=8788 RBI_SANS_COMPTES=1 node loge/serveur/faux-serveur.mjs &
#   RBI_PORT=8789 node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-verrou.py
#
# DEUX PANNES, VÉCUES L'UNE ET L'AUTRE :
#
#  1. LA TABLE DES UTILISATEURS EST VIDE. Le serveur répond, et refuse
#     tout le monde. La porte interrogeait le serveur d'abord et
#     s'arrêtait à son refus : plus personne n'entrait, alors que le
#     mot de passe de la page était juste. C'est arrivé le premier
#     soir, à la Sœur Secrétaire.
#
#  2. ON RECHARGE LA PAGE. La porte se souvenait du rôle, mais le lien
#     avec le serveur, lui, ne se rétablissait pas : on retravaillait
#     sur le seul appareil en croyant le registre partagé. Deux
#     Officiers pouvaient diverger sans que rien ne le dise.
from playwright.sync_api import sync_playwright
import os

SANS = os.environ.get("RBI_URL_SANS", "http://127.0.0.1:8788/")
AVEC = os.environ.get("RBI_URL_AVEC", "http://127.0.0.1:8789/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
ko = []

def v(c, n, d=''):
    print(f"  {'✓' if c else '✗'} {n}{'' if c else '  <- ' + str(d)[:220]}")
    if not c: ko.append(n)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    # ══ 1. LE SERVEUR REFUSE TOUT LE MONDE ══════════════════════════
    c1 = b.new_context(); M = c1.new_page()
    err1 = []; M.on("pageerror", lambda e: err1.append(str(e)))
    M.on("dialog", lambda d: d.accept())
    M.goto(SANS); M.wait_for_timeout(900)

    refus = M.evaluate("""async () => {
      const r = await fetch('/api/entrer', { method:'POST',
        headers:{'content-type':'application/json'},
        body: JSON.stringify({ mdp:'cleSecretariatEpreuve' }) });
      return r.status;
    }""")
    v(refus == 401, "le serveur d'épreuve refuse bien : la panne est reproduite", refus)

    M.fill("#porte-mdp", "cleSecretariatEpreuve")
    M.click("#porte-form button[type=submit]"); M.wait_for_timeout(1800)
    v(M.locator("#appli").is_visible(),
      "MARTINE ENTRE QUAND MÊME : un serveur mal réglé ne l'enferme plus dehors")
    v(M.evaluate("SERVEUR.repli") is True, "et le programme sait qu'il s'est replié")
    v(M.evaluate("SERVEUR.actif") is False, "sans prétendre que le registre répond")
    ban = M.locator("#alerte-repli")
    v(ban.count() == 1 and ban.is_visible(), "un bandeau le dit à l'écran")
    t = ban.inner_text() if ban.count() else ''
    v("hors service" in t, "il annonce que le registre partagé est hors service", t)
    v("cet appareil" in t, "que le travail reste sur cet appareil seul", t)
    v("Sauvegarder mes données" in t, "et il dit quoi faire : sauvegarder", t)
    v("Enregistré" not in M.inner_text("#etat-sauvegarde"),
      "le pied de page ne ment pas : il ne dit pas « Enregistré »",
      M.inner_text("#etat-sauvegarde"))

    # elle travaille : rien ne doit partir au serveur, tout doit tenir
    M.click("#t-tableau"); M.wait_for_timeout(400)
    M.set_input_files("#fichier-sauvegarde", TABLEAU); M.wait_for_timeout(2000)
    M.click("#t-tableau"); M.wait_for_timeout(500)
    v(M.locator("#v-tableau tbody tr").count() == 12,
      "elle peut travailler : les douze fiches sont là",
      M.locator("#v-tableau tbody tr").count())
    v(M.locator("#alerte-repli").count() == 1,
      "et le bandeau ne disparaît pas quand on change d'onglet")

    # un mot de passe faux reste faux, serveur en panne ou non
    c2 = b.new_context(); X = c2.new_page()
    X.goto(SANS); X.wait_for_timeout(900)
    X.fill("#porte-mdp", "pasbon"); X.click("#porte-form button[type=submit]")
    X.wait_for_timeout(1500)
    v(not X.locator("#appli").is_visible(),
      "le repli n'ouvre pas la porte à n'importe qui : un faux mot de passe est refusé")

    # ══ 2. ON RECHARGE LA PAGE, SERVEUR EN ÉTAT ═════════════════════
    c3 = b.new_context(); S = c3.new_page()
    err3 = []; S.on("pageerror", lambda e: err3.append(str(e)))
    S.on("dialog", lambda d: d.accept())
    S.goto(AVEC); S.wait_for_timeout(900)
    S.fill("#porte-mdp", "cleSecretariatEpreuve"); S.click("#porte-form button[type=submit]")
    S.wait_for_timeout(1500)
    v(S.evaluate("SERVEUR.actif") is True, "Martine entre par le serveur")
    S.click("#t-tableau"); S.wait_for_timeout(400)
    S.set_input_files("#fichier-sauvegarde", TABLEAU); S.wait_for_timeout(2200)
    av = S.evaluate("SERVEUR.version")
    v(av >= 1, "le tableau est monté au registre", av)

    S.reload(); S.wait_for_timeout(2200)
    v(S.locator("#appli").is_visible(), "après rechargement, elle n'a rien à retaper")
    v(S.evaluate("SERVEUR.actif") is True,
      "ET LE LIEN AVEC LE REGISTRE EST REPRIS : plus de travail solitaire ignoré",
      S.evaluate("SERVEUR.actif"))
    v(S.evaluate("SERVEUR.version") >= av,
      "sur la bonne version", S.evaluate("SERVEUR.version"))
    v(S.evaluate("SERVEUR.nom") == "Sœur Secrétaire d’épreuve",
      "et le serveur redit qui elle est", S.evaluate("SERVEUR.nom"))
    v("Enregistré" in S.inner_text("#etat-sauvegarde"),
      "le témoin le dit", S.inner_text("#etat-sauvegarde"))
    v(S.locator("#v-tableau tbody tr").count() == 12,
      "le tableau est toujours là", S.locator("#v-tableau tbody tr").count())

    # une saisie faite après le rechargement repart bien au serveur
    S.click('tr[data-fiche="7"]'); S.wait_for_timeout(400)
    S.fill("#m-email", "zayin@exemple.test"); S.wait_for_timeout(2000)
    v(S.evaluate("SERVEUR.version") > av,
      "et ce qu'elle saisit ensuite monte au registre", S.evaluate("SERVEUR.version"))
    lu = S.evaluate("""async () => (await (await fetch('/api/etat',
      {credentials:'same-origin'})).json())""")
    v(any(m.get("email") == "zayin@exemple.test" for m in lu["donnees"]["membres"]),
      "le registre le porte vraiment")

    # ══ 3. LA SESSION A EXPIRÉ : on redemande le mot de passe ════════
    S.context.clear_cookies()
    S.reload(); S.wait_for_timeout(2200)
    v(S.locator("#porte").is_visible(),
      "session perdue : LA PORTE SE REFERME, au lieu de laisser croire au partage")
    v(not S.locator("#appli").is_visible(), "le programme n'est pas ouvert")
    v("expiré" in S.inner_text("#porte-erreur"),
      "et l'on dit pourquoi", S.inner_text("#porte-erreur"))
    v("conservé sur cet appareil" in S.inner_text("#porte-erreur"),
      "en rassurant sur le travail en cours", S.inner_text("#porte-erreur"))

    v(not err1 and not err3, "aucune erreur JavaScript", err1 + err3)
    b.close()

print(f"\n  {len(ko)} échec(s)" if ko else "\n  tout passe")
