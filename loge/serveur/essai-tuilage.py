# L'EPREUVE DES DEUX PORTES DE TUILAGE
#
#   node loge/serveur/faux-page.mjs > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8800 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-tuilage.py
#
# Le site a DEUX portes qui posent les memes questions : celle de
# l'accueil, batie depuis assets/config.js, et celle de l'Espace
# Membres, ecrite dans sa page. Changer la question a un endroit et
# l'oublier a l'autre laisserait une porte sur l'ancienne reponse —
# et personne ne s'en apercevrait avant qu'un Frere reste dehors.
#
# On eprouve donc LES DEUX, et l'on eprouve aussi ce qui doit RESTER
# ferme : « minuit » est l'heure de clore les travaux, non de les
# ouvrir.
from playwright.sync_api import sync_playwright
import os

U = os.environ.get("RBI_URL", "http://127.0.0.1:8800/")
ko = []


def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:240]}")
    if not c:
        ko.append(n)


OUVRE = ["midi", "à midi", "A MIDI", "de midi à minuit", "en plein midi"]
FERME = ["minuit", "à minuit", "le matin", "9h", "de saint jean",
         "de la loge de St Jean"]

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    errs = []

    # == 1. LA PORTE DE L'ACCUEIL ====================================
    pg = b.new_context().new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(U + "index.html"); pg.wait_for_timeout(1500)

    q1 = pg.inner_text("#tuilage-q1") if pg.locator("#tuilage-q1").count() else ''
    v("quelle heure commencez-vous à travailler" in q1.lower(),
      "L'ACCUEIL POSE LA NOUVELLE QUESTION", q1[:120])
    v("venez-vous" not in q1.lower() and "jean" not in q1.lower(),
      "et plus l'ancienne", q1[:120])

    def accueil(reponse):
        pg.goto(U + "index.html"); pg.wait_for_timeout(1200)
        pg.click("#tuilage-start-btn"); pg.wait_for_timeout(500)
        pg.fill("#tuilage-input-1", reponse)
        pg.click("#tuilage-btn-1"); pg.wait_for_timeout(1400)
        # la question de l'âge ne parait que si la première est passée
        return not pg.locator("#tuilage-q2").first.evaluate(
            "el => el.classList.contains('tuilage__step--hidden')")

    for r in OUVRE:
        v(accueil(r), f"« {r} » passe la première question")
    for r in FERME:
        v(not accueil(r), f"« {r} » ne passe pas")

    # jusqu'au bout : l'âge, puis la reconnaissance
    pg.goto(U + "index.html"); pg.wait_for_timeout(1200)
    pg.click("#tuilage-start-btn"); pg.wait_for_timeout(400)
    pg.fill("#tuilage-input-1", "à midi"); pg.click("#tuilage-btn-1")
    pg.wait_for_timeout(1400)
    pg.fill("#tuilage-input-2", "7 ans"); pg.click("#tuilage-btn-2")
    pg.wait_for_timeout(1600)
    v(not pg.locator("#tuilage-success").evaluate(
        "el => el.classList.contains('tuilage__step--hidden')"),
      "MIDI PUIS L'ÂGE : le Frère est reconnu")

    # == 2. LA PORTE DE L'ESPACE MEMBRES =============================
    def membres(r1, r2="7 ans"):
        p2 = b.new_context().new_page()
        p2.on("pageerror", lambda e: errs.append(str(e)))
        p2.goto(U + "espace-membres.html"); p2.wait_for_timeout(1000)
        libelle = p2.inner_text("label[for=porte-q1]")
        p2.fill("#porte-q1", r1); p2.fill("#porte-q2", r2)
        p2.click("#porte-form button[type=submit]"); p2.wait_for_timeout(900)
        ouvert = p2.locator("#contenu-membres").is_visible()
        p2.close()
        return ouvert, libelle

    ouvert, libelle = membres("à midi")
    v("quelle heure commencez-vous à travailler" in libelle.lower(),
      "L'ESPACE MEMBRES POSE LA MÊME QUESTION, MOT POUR MOT", libelle)
    v(ouvert, "et « à midi » l'ouvre")

    for r in ["midi", "de midi à minuit", "EN PLEIN MIDI"]:
        v(membres(r)[0], f"« {r} » ouvre l'Espace Membres")
    for r in ["minuit", "de saint jean", "le matin"]:
        v(not membres(r)[0], f"« {r} » ne l'ouvre pas")

    v(not membres("à midi", "9 ans")[0],
      "et l'âge est toujours demandé : midi seul ne suffit pas")

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
