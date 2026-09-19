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
    "amis": [
        {"nom": "RAHAMIM", "prenom": "Tikva", "email": "tikva@exemple.test",
         "tel": "06 00 00 00 44"},
        {"nom": "SHALOM", "prenom": "Ora", "email": "", "tel": "",
         "notes": "Aucune adresse courriel dans le document : injoignable."},
    ],
    "reglages": {"motFin": "Mention d'epreuve, avec un numero au 06 00 00 00 00."},
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
    v(pg.evaluate("(E.amis||[]).length") == 2,
      "ET LES DEUX AMIS DE LA LOGE : ni membres, ni visiteurs",
      pg.evaluate("(E.amis||[]).length"))
    v(pg.evaluate("E.visiteurs.some(v=>v.nom==='RAHAMIM')") is False,
      "un Ami n'entre PAS au carnet des visiteurs : il n'est jamais venu en tenue")

    # == LES REGLAGES VONT AU REGISTRE, PAS AU PROGRAMME ============
    v("06 00 00 00 00" in pg.evaluate("E.tenue.motFin"),
      "LE CARNET PEUT PORTER LA MENTION DU BAS DE CONVOCATION, "
      "numero compris — elle vit dans le registre",
      pg.evaluate("E.tenue.motFin"))
    v("06 00 00 00 00" not in pg.evaluate("document.documentElement.outerHTML")
      .replace(pg.evaluate("E.tenue.motFin"), ""),
      "et ce numero n'est nulle part dans le programme lui-meme")

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

    # == LA FICHE D'UN AMI S'OUVRE, ET SE MODIFIE ===================
    # Deux defauts, l'un derriere l'autre, et aucun ne disait rien.
    #
    # 1. Le test de la ligne etait place APRES « si ce n'est pas un
    #    bouton, on sort ». Une ligne de tableau n'est pas un bouton :
    #    la fiche ne s'ouvrait JAMAIS.
    # 2. Deux fonctions portaient le nom « aChamp » — l'une pour les
    #    Amis, l'autre pour les Loges amies. La seconde ecrasait la
    #    premiere : les champs d'un Ami se dessinaient avec les
    #    etiquettes des Loges, et la saisie partait dans la mauvaise
    #    branche. AUCUN AMI NE POUVAIT ETRE MODIFIE.
    pg.evaluate("""() => { E.amiOuvert = null;
      E.amis = [{ id: 811, nom: 'CCC', prenom: 'Trois',
                  email: 'c@x.test', tel: '', notes: '' }];
      garder(); dessiner(); }""")
    pg.wait_for_timeout(600)
    pg.click("#t-amis"); pg.wait_for_timeout(600)
    pg.click("tr[data-ami-ligne='811']"); pg.wait_for_timeout(900)
    v(pg.evaluate("E.amiOuvert") == 811,
      "LA FICHE D'UN AMI S'OUVRE quand on clique sa ligne",
      pg.evaluate("E.amiOuvert"))
    champs = pg.evaluate("[...document.querySelectorAll('[data-ami]')].map(e=>e.dataset.ami)")
    v(sorted(champs) == ["email", "nom", "notes", "prenom", "tel"],
      "et elle porte ses cinq champs, aux etiquettes des Amis", champs)

    pg.fill("#f-ami-tel", "06 12 34 56 78"); pg.wait_for_timeout(600)
    v(pg.evaluate("(E.amis||[]).find(a=>a.id===811).tel") == "06 12 34 56 78",
      "LE TELEPHONE S'ENREGISTRE",
      pg.evaluate("(E.amis||[]).find(a=>a.id===811).tel"))
    pg.fill("#f-ami-email", "neuf@x.test"); pg.wait_for_timeout(600)
    v(pg.evaluate("(E.amis||[]).find(a=>a.id===811).email") == "neuf@x.test",
      "l'adresse aussi — c'est elle qui porte la convocation",
      pg.evaluate("(E.amis||[]).find(a=>a.id===811).email"))
    pg.fill("#f-ami-nom", "ZZZ"); pg.wait_for_timeout(800)
    v(pg.evaluate("(E.amis||[]).find(a=>a.id===811).nom") == "ZZZ",
      "et le nom, sans que la fiche se referme sous les doigts",
      pg.evaluate("(E.amis||[]).find(a=>a.id===811).nom"))
    v(pg.evaluate("E.amiOuvert") == 811,
      "la fiche reste ouverte pendant qu'on ecrit")
    pg.evaluate("() => { E.amiOuvert = null; dessiner(); }")
    pg.wait_for_timeout(500)

    # == ON RETIRE DEPUIS LA LISTE, NON DEPUIS LA FICHE =============
    # Le bouton « Retirer » n'existait que dans la fiche ouverte :
    # trouver la ligne parmi quatre-vingt-dix, l'ouvrir, descendre,
    # confirmer, revenir. Cinq gestes pour en retirer un. La croix est
    # au bout de la ligne — et elle arrete le clic avant qu'il n'ouvre
    # la fiche, sans quoi on retirerait ET l'on ouvrirait.
    pg.evaluate("""() => {
      E.amis = [{ id: 801, nom: 'AAA', prenom: 'Un', email: 'a@x.test' },
                { id: 802, nom: 'BBB', prenom: 'Deux', email: 'b@x.test' }];
      E.reponsesAmis = { 801: { reponse: 'present', agapes: true } };
      E.visiteurs = [{ id: 701, nom: 'VVV', prenom: 'Vis', email: 'v@x.test',
                       venuDeLAnnuaire: true, visites: [] }];
      E.agapesVisiteurs = { 701: true };
      garder(); dessiner(); }""")
    pg.wait_for_timeout(600)

    pg.click("#t-amis"); pg.wait_for_timeout(600)
    v(pg.locator("[data-ami-retirer]").count() == 2,
      "CHAQUE AMI PORTE SA CROIX, dans la liste")
    pg.click("[data-ami-retirer='801']"); pg.wait_for_timeout(900)
    v(pg.evaluate("(E.amis||[]).map(a=>a.nom)") == ["BBB"],
      "un Ami se retire d'un geste", pg.evaluate("(E.amis||[]).map(a=>a.nom)"))
    v(pg.evaluate("!(E.reponsesAmis||{})[801]"),
      "et sa reponse aux agapes s'en va avec lui : le traiteur ne "
      "comptera pas un couvert pour un absent du carnet")
    v(pg.evaluate("!E.amiOuvert"),
      "LA CROIX N'OUVRE PAS LA FICHE : le clic est arrete avant la ligne")

    pg.click("#t-visiteurs"); pg.wait_for_timeout(600)
    v(pg.locator("[data-vis-retirer]").count() == 1,
      "chaque Visiteur porte la sienne")
    pg.click("[data-vis-retirer='701']"); pg.wait_for_timeout(900)
    v(pg.evaluate("(E.visiteurs||[]).length") == 0,
      "un Visiteur venu de l'annuaire se retire de meme",
      pg.evaluate("(E.visiteurs||[]).length"))
    v(pg.evaluate("!(E.agapesVisiteurs||{})[701]"),
      "et son couvert avec lui")

    # == LES AMIS SE LISENT, DONC ILS SE RANGENT ====================
    # Ils arrivaient dans l'ordre ou on les avait saisis, ou verses d'un
    # carnet : quatre-vingt-dix noms dans le desordre du hasard, qu'on
    # parcourait a l'oeil. Le registre garde son ordre d'arrivee — qui
    # est une date, donc une trace ; c'est l'ECRAN qui se range.
    pg.evaluate("""() => { E.amis = [
        { id: 901, nom: 'ZOHAR',  prenom: 'Aaron' },
        { id: 902, nom: 'élie',   prenom: 'Sarah' },
        { id: 903, nom: 'ABBOU',  prenom: 'Myriam' },
        { id: 904, nom: 'Elie',   prenom: 'David' },
        { id: 905, nom: 'MERCIER', prenom: 'Paul' } ];
      garder(); dessiner(); }""")
    pg.wait_for_timeout(700)
    pg.click("#t-amis"); pg.wait_for_timeout(700)
    # on lit les NOMS dans l'ordre ou l'ecran les pose, non le texte
    # affiche : la cellule porte « Prenom NOM », et c'est le nom qui range.
    ordre = pg.evaluate("""() => [...document.querySelectorAll('[data-ami-ligne]')]
        .map(t => +t.dataset.amiLigne)
        .map(id => (E.amis.find(a => a.id === id) || {}).nom)""")
    v(len(ordre) == 5, "les cinq Amis sont a l'ecran", ordre)
    v(ordre == ["ABBOU", "Elie", "élie", "MERCIER", "ZOHAR"] or
      ordre == ["ABBOU", "élie", "Elie", "MERCIER", "ZOHAR"],
      "LES AMIS SONT RANGES PAR ORDRE ALPHABETIQUE", ordre)
    v(ordre[0] == "ABBOU", "le premier est bien le premier", ordre)
    v(ordre[-1] == "ZOHAR", "et le dernier le dernier", ordre)
    v(ordre.index("MERCIER") > max(ordre.index("Elie"), ordre.index("élie")),
      "ET LES ACCENTS SE RANGENT COMME EN FRANCAIS : elie pres d Elie, "
      "non rejete a la fin", ordre)
    v(pg.evaluate("(E.amis||[]).map(a => a.id)") == [901, 902, 903, 904, 905],
      "mais le registre garde son ordre d'arrivee : c'est une trace",
      pg.evaluate("(E.amis||[]).map(a => a.id)"))

    v(not errs, "aucune erreur JavaScript", errs)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
