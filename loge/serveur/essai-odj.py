# L'EPREUVE DU RANGEMENT DE L'ORDRE DU JOUR
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8801 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-odj.py
#
# Une ligne ajoutee apres coup se retrouvait en bas : la convocation
# annoncait l'accueil sur le parvis APRES les agapes. On range donc.
#
# CE QUI COMPTE LE PLUS : ce qui n'a pas d'heure ne bouge pas. Un point
# sans horaire n'a pas de place dans le temps ; le deplacer serait
# decider a la place de la Secretaire.
from playwright.sync_api import sync_playwright
import os

U = os.environ.get("RBI_URL", "http://127.0.0.1:8801/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []


def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:260]}")
    if not c:
        ko.append(n)


# Le desordre du jour : l'accueil de 19:15 saisi en dernier, et deux
# points sans heure au milieu.
DESORDRE = [
    {"h": "19:30", "t": "Ouverture"},
    {"h": "",      "t": "Divers"},
    {"h": "23:00", "t": "Agapes"},
    {"h": "20:00", "t": "Symbolisme"},
    {"h": "",      "t": "Questions"},
    {"h": "19:15", "t": "Accueil sur les parvis"},
]

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_context().new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    dlg = []
    pg.on("dialog", lambda d: (dlg.append(d.message), d.accept()))

    pg.goto(U); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1800)
    pg.click("#t-tableau"); pg.wait_for_timeout(400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU); pg.wait_for_timeout(2500)

    pg.evaluate("(o) => { E.odj = o; garder(); dessiner(); }", DESORDRE)
    pg.click("#t-convoc"); pg.wait_for_timeout(800)

    # == 1. LA LECTURE DE L'HEURE ====================================
    for h, att in [("19:30", 1170), ("9:05", 545), ("19h30", 1170),
                   ("", None), ("Divers", None), ("25:00", None), ("19:75", None)]:
        got = pg.evaluate("(h) => minutesDe(h)", h)
        v(got == att, f"« {h or '(vide)'} » se lit {att}", got)

    # == 2. LES DOCUMENTS SE RANGENT SANS QU'ON DEMANDE RIEN ========
    lu = pg.evaluate("() => odjRange().map(o => (o.h || '—') + ' ' + o.t)")
    brut = pg.evaluate("() => E.odj.map(o => (o.h || '—') + ' ' + o.t)")
    v(lu[0].startswith("19:15"),
      "LA LECTURE EST RANGEE D'ELLE-MEME, sans qu'on ait rien demande", lu[0])
    v(brut[0].startswith("19:30"),
      "MAIS LE REGISTRE N'A PAS BOUGE : la saisie reste ou on l'a mise", brut[0])

    pg.click("#imp-convoc"); pg.wait_for_timeout(900)
    t0 = pg.inner_text(".papier")
    v(0 <= t0.find("Accueil sur les parvis") < t0.find("Ouverture"),
      "et la convocation sort dans l'ordre du temps sans un geste")
    pg.click("#fermer"); pg.wait_for_timeout(300)

    # == 3. LE BOUTON RANGE AUSSI LE REGISTRE ========================
    bouge = pg.evaluate("() => rangerOdj()")
    v(bouge > 0, "le rangement deplace bien quelque chose", bouge)
    apres = pg.evaluate("() => E.odj.map(o => (o.h || '—') + ' ' + o.t)")
    print("     ", " | ".join(apres))

    heures = [x for x in pg.evaluate("() => E.odj.map(o => o.h)") if x]
    v(heures == sorted(heures),
      "LES LIGNES HORODATEES SONT DANS L'ORDRE DU TEMPS", heures)
    v(apres[0].startswith("19:15"),
      "l'accueil de 19:15 est remonte en tete", apres[0])

    # ce qui n'a pas d'heure n'a pas bouge
    v(apres[1] == "— Divers",
      "« Divers » N'A PAS BOUGE : il n'avait pas d'heure", apres[1])
    v(apres[4] == "— Questions",
      "« Questions » non plus", apres[4])

    v(len(apres) == len(DESORDRE),
      "aucune ligne n'est perdue ni dupliquee", len(apres))
    v(sorted(x.split(' ', 1)[1] for x in apres) ==
      sorted(o["t"] for o in DESORDRE),
      "et ce sont bien les memes points")

    # == 4. LE DOCUMENT SUIT =========================================
    pg.click("#imp-convoc"); pg.wait_for_timeout(900)
    t = pg.inner_text(".papier")
    i_accueil, i_ouv = t.find("Accueil sur les parvis"), t.find("Ouverture")
    v(0 <= i_accueil < i_ouv,
      "LA CONVOCATION IMPRIMEE SUIT LE MEME ORDRE", (i_accueil, i_ouv))
    pg.click("#fermer"); pg.wait_for_timeout(300)

    txt = pg.evaluate("() => convocationTexte()")
    v(txt.find("Accueil sur les parvis") < txt.find("Ouverture"),
      "et le courriel aussi")

    # == 5. RANGER DEUX FOIS NE CHANGE RIEN ==========================
    dlg.clear()
    encore = pg.evaluate("() => rangerOdj()")
    v(encore == 0, "un second rangement ne deplace plus rien", encore)
    pg.click("#t-convoc"); pg.wait_for_timeout(600)
    pg.click("#odj-ranger"); pg.wait_for_timeout(900)
    v(any("deja range" in d.replace("é", "e").replace("à", "a") for d in dlg),
      "et le bouton le dit au lieu de faire semblant", dlg)

    # == 6. UN ORDRE DU JOUR SANS AUCUNE HEURE ======================
    pg.evaluate("""() => { E.odj = [{h:'',t:'Un'},{h:'',t:'Deux'}];
      garder(); dessiner(); }""")
    pg.wait_for_timeout(500)
    v(pg.evaluate("() => rangerOdj()") == 0,
      "sans aucune heure, rien ne bouge et rien ne casse")
    v(pg.evaluate("() => E.odj.map(o=>o.t).join(',')") == "Un,Deux",
      "l'ordre saisi est respecte")

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
