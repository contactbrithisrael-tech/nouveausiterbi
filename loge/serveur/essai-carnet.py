# L'EPREUVE DU CARNET DE CONTACTS
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8793 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-carnet.py
#
# DEUX SORTES DE FICHIERS, ET ILS NE FONT PAS LA MEME CHOSE.
#
# Une SAUVEGARDE porte tout l'Atelier et REMPLACE ce qui est la.
# Un CARNET ne porte que des Visiteurs et des Loges amies, et S'AJOUTE.
#
# Les confondre couterait le Tableau de la Loge : charger un carnet
# comme une sauvegarde effacerait les douze fiches de membres pour y
# mettre seize visiteurs. C'est ce que cette epreuve verifie d'abord.
from playwright.sync_api import sync_playwright
import json, os, tempfile

U = os.environ.get("RBI_URL", "http://127.0.0.1:8793/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []


def v(c, n, d=''):
    print(f"  {'OK' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:220]}")
    if not c:
        ko.append(n)


CARNET = {
    "_format": "carnet-loge-rbi", "_version": 1,
    "_origine": "Tableur d'epreuve",
    "_reserves": "2 fiche(s) portent une reserve de lecture.",
    "visiteurs": [
        {"nom": "TSEDEK", "prenom": "Nekouda", "grade": "M",
         "loge": "L EXEMPLE", "tel": "06 00 00 00 11",
         "email": "nekouda@exemple.test"},
        {"nom": "EMOUNA", "prenom": "Otiya", "grade": "C", "loge": "L SECONDE",
         "tel": "", "email": "",
         "note": "Adresse relevee au document, inutilisable en l'etat."},
        {"nom": "HESSED", "prenom": "Gvoul", "grade": "A", "loge": "L TROISIEME",
         "tel": "06 00 00 00 33", "email": "gvoul@exemple.test",
         "note": "Nom de Loge lu par deduction."},
    ],
    "amies": [
        {"nom": "L EXEMPLE", "notes": "Relevee au tableur."},
        {"nom": "L SECONDE", "notes": "Relevee au tableur."},
    ],
}

with sync_playwright() as b0:
    b = b0.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context()
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    dialogues = []
    pg.on("dialog", lambda d: (dialogues.append(d.message), d.accept()))

    chemin = os.path.join(tempfile.gettempdir(), "carnet-epreuve.json")
    json.dump(CARNET, open(chemin, "w", encoding="utf-8"), ensure_ascii=False)

    pg.goto(U)
    pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE)
    pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1500)

    # le Tableau de la Loge, charge d'abord : c'est lui qu'un carnet
    # mal traite ferait disparaitre.
    pg.click("#t-tableau")
    pg.wait_for_timeout(400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU)
    pg.wait_for_timeout(2500)
    avant_membres = pg.evaluate("E.membres.length")
    avant_vis = pg.evaluate("E.visiteurs.length")
    v(avant_membres == 12, "le Tableau porte douze membres avant tout", avant_membres)

    # == 1. LE CARNET S'AJOUTE ======================================
    dialogues.clear()
    pg.set_input_files("#fichier-sauvegarde", chemin)
    pg.wait_for_timeout(2000)
    demande = dialogues[0] if dialogues else ''
    v("Ajouter ce carnet" in demande,
      "on demande AVANT de verser, et l'on dit quoi", demande[:140])
    v("RIEN NE SERA" in demande.upper(),
      "en annoncant que rien ne sera efface", demande[:200])
    v("Tableur d'epreuve" in demande, "et d'ou vient le carnet", demande[:200])

    v(pg.evaluate("E.membres.length") == 12,
      "LE TABLEAU DE LA LOGE EST INTACT : un carnet n'efface pas les membres",
      pg.evaluate("E.membres.length"))
    v(pg.evaluate("E.visiteurs.length") == avant_vis + 3,
      "les trois visiteurs sont verses au carnet",
      pg.evaluate("E.visiteurs.length"))
    v(pg.evaluate("E.amies.length") >= 2, "et les deux Loges amies",
      pg.evaluate("E.amies.length"))

    bilan = dialogues[-1] if dialogues else ''
    v("3 ajout" in bilan.replace("\u00e9",""), 
      "on dit combien ont ete verses", bilan[:160])
    v("reserve" in bilan, "et l'on rappelle les reserves de lecture", bilan[:200])

    # == 2. LES RESERVES SUIVENT LA FICHE ===========================
    note = pg.evaluate(
        "E.visiteurs.find(x=>x.nom==='EMOUNA').note || ''")
    v("inutilisable" in note, "LA RESERVE EST PORTEE SUR LA FICHE", note[:120])
    v(pg.evaluate("E.visiteurs.find(x=>x.nom==='EMOUNA').email") == "",
      "ET L'ADRESSE ILLISIBLE N'EST PAS INSCRITE COMME UNE ADRESSE : "
      "on ecrirait a personne")

    pg.click("#t-visiteurs")
    pg.wait_for_timeout(600)
    import unicodedata
    sansacc = lambda t: "".join(c for c in unicodedata.normalize("NFD", t)
                                if not unicodedata.combining(c))
    liste = sansacc(pg.inner_text("#v-visiteurs"))
    v("a verifier" in liste, "et la liste marque ces fiches", liste[:300])

    idv = pg.evaluate("E.visiteurs.find(x=>x.nom==='EMOUNA').id")
    pg.click(f'tr[data-vis="{idv}"] td:first-child')
    pg.wait_for_timeout(600)
    fsans = sansacc(pg.inner_text("#v-visiteurs"))
    v("verifier" in fsans and "inutilisable" in fsans,
      "la fiche montre ce qui reste a verifier", fsans[:400])
    pg.click("#vis-retour")
    pg.wait_for_timeout(400)

    # == 3. LE MEME CARNET DEUX FOIS NE DOUBLE RIEN =================
    combien = pg.evaluate("E.visiteurs.length")
    dialogues.clear()
    pg.set_input_files("#fichier-sauvegarde", chemin)
    pg.wait_for_timeout(2000)
    v(pg.evaluate("E.visiteurs.length") == combien,
      "LE MEME CARNET VERSE DEUX FOIS N'AJOUTE PERSONNE",
      pg.evaluate("E.visiteurs.length"))
    v("0 ajout" in (dialogues[-1] if dialogues else ''),
      "et le bilan le dit", dialogues[-1][:140] if dialogues else '')

    # == 4. CE QU'UNE MAIN A CORRIGE L'EMPORTE ======================
    pg.evaluate("""() => { const x = E.visiteurs.find(v=>v.nom==='TSEDEK');
      x.grade = 'Maitre Macon verifie'; garder(); }""")
    pg.wait_for_timeout(600)
    dialogues.clear()
    pg.set_input_files("#fichier-sauvegarde", chemin)
    pg.wait_for_timeout(2000)
    v(pg.evaluate("E.visiteurs.find(v=>v.nom==='TSEDEK').grade")
      == "Maitre Macon verifie",
      "CE QU'UNE MAIN A CORRIGE N'EST PAS ECRASE par un nouveau versement",
      pg.evaluate("E.visiteurs.find(v=>v.nom==='TSEDEK').grade"))

    # mais ce qui manquait est complete
    pg.evaluate("""() => { const x = E.visiteurs.find(v=>v.nom==='HESSED');
      x.tel = ''; garder(); }""")
    pg.wait_for_timeout(600)
    dialogues.clear()
    pg.set_input_files("#fichier-sauvegarde", chemin)
    pg.wait_for_timeout(2000)
    v(pg.evaluate("E.visiteurs.find(v=>v.nom==='HESSED').tel") == "06 00 00 00 33",
      "tandis qu'un champ vide est complete",
      pg.evaluate("E.visiteurs.find(v=>v.nom==='HESSED').tel"))

    # == 5. UNE SAUVEGARDE, ELLE, REMPLACE TOUJOURS =================
    dialogues.clear()
    pg.set_input_files("#fichier-sauvegarde", TABLEAU)
    pg.wait_for_timeout(2500)
    v("remplac" in (dialogues[0] if dialogues else '').lower(),
      "une SAUVEGARDE previent qu'elle remplace",
      dialogues[0][:140] if dialogues else '')
    v(pg.evaluate("E.visiteurs.length") == 3,
      "et elle remplace bien : on retrouve le tableau seul",
      pg.evaluate("E.visiteurs.length"))

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
