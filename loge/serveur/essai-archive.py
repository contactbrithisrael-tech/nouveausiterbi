# L'EPREUVE DES TENUES PASSEES
#
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8812 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-archive.py
#
# CE QUI SE PERDAIT. Le registre ne portait QU'UNE tenue : ses
# presences, ses agapes, ses reponses etaient des cases uniques,
# rattachees a « la » tenue. Le jour ou la Secretaire saisissait la date
# de la suivante, tout basculait dessus — et LA PLANCHE A TRACER de la
# tenue qui venait d'avoir lieu devenait irreproductible.
#
# Une planche a tracer est le proces-verbal des travaux de l'Atelier.
# Ce n'etait donc pas une commodite perdue : c'etait l'archive de la
# Loge qui s'effacait, en silence, d'une frappe au clavier.
from playwright.sync_api import sync_playwright
import os

U = os.environ.get("RBI_URL", "http://127.0.0.1:8812/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []

def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:280]}")
    if not c: ko.append(n)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    c = b.new_context(); pg = c.new_page()
    e = []; pg.on("pageerror", lambda x: e.append(str(x)))
    d = []; pg.on("dialog", lambda x: (d.append(x.message), x.accept()))
    pg.goto(U); pg.wait_for_timeout(800)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(2400)
    pg.set_input_files("#fichier-sauvegarde", TABLEAU); pg.wait_for_timeout(2800)

    # ══ 1. UNE TENUE A LIEU ═════════════════════════════════════════
    JOUR = pg.evaluate("E.tenue.date")
    pg.evaluate("""() => {
      const m = convocables();
      E.presences[m[0].id] = 'present';
      E.presences[m[1].id] = 'present';
      E.presences[m[2].id] = 'excuse';
      E.agapes[m[0].id] = true;
      E.convoquee = true;
      const vi = E.visiteurs[0];
      vi.presentTenue = true; vi.tuilePar = 'Guimel KISLEV';
      garder(); }""")
    pg.wait_for_timeout(1500)
    nomVisiteur = pg.evaluate("E.visiteurs[0].nom")
    planche = pg.evaluate("corpsPlanche()")
    v(nomVisiteur in planche,
      "la planche a tracer de cette tenue porte le Visiteur qui etait la",
      nomVisiteur)

    # ══ 2. LA SECRETAIRE SAISIT LA DATE DE LA SUIVANTE ══════════════
    # C'est le geste qui effaçait tout, et personne ne le savait.
    pg.click("#t-convoc"); pg.wait_for_timeout(800)
    pg.fill("[data-t='date']", "2027-01-11")
    pg.wait_for_timeout(1800)

    v(pg.evaluate("E.tenue.date") == "2027-01-11",
      "la nouvelle date est prise", pg.evaluate("E.tenue.date"))
    arch = pg.evaluate("(E.tenuesPassees || []).map(a => a.tenue.date)")
    v(JOUR in arch,
      "ET LA TENUE PRECEDENTE EST CLASSEE, sans qu'on ait rien demande", arch)

    v(pg.evaluate("Object.keys(E.presences).length") == 0,
      "LA TENUE NEUVE PART D'UNE FEUILLE BLANCHE : les presents de la "
      "precedente ne sont pas les siens",
      pg.evaluate("E.presences"))
    v(pg.evaluate("E.convoquee") is False,
      "et elle n'est pas deja convoquee")
    v(pg.evaluate("E.visiteurs.every(x => !x.presentTenue)"),
      "ni les Visiteurs deja attendus")
    v(pg.evaluate("(E.journal||[]).some(x => x.indexOf('classée') >= 0)"),
      "le journal dit que la tenue a ete classee",
      pg.evaluate("(E.journal||[])[0]"))

    # ══ 3. ET SA PLANCHE A TRACER SE REFAIT A L'IDENTIQUE ═══════════
    # C'est tout l'objet : le proces-verbal des travaux d'un soir doit
    # pouvoir se reproduire six mois plus tard.
    pg.click("#t-tenue"); pg.wait_for_timeout(900)
    v(pg.locator("#t-tenues-passees").count() == 1,
      "l'ecran porte un tableau des Tenues passees")
    v(pg.locator(f"button[data-passee-planche]").count() >= 1,
      "avec un bouton par tenue pour sa planche a tracer")

    refaite = pg.evaluate("""(jour) => {
      const a = E.tenuesPassees.find(x => x.tenue.date === jour);
      return avecLaTenuePassee(a, () => corpsPlanche()); }""", JOUR)
    v(nomVisiteur in refaite,
      "LA PLANCHE DE LA TENUE CLASSEE PORTE ENCORE LE VISITEUR QUI ETAIT LA",
      nomVisiteur)
    v(refaite == planche,
      "ET ELLE EST IDENTIQUE A CELLE D'ALORS, mot pour mot : ce sont les "
      "memes faits qui la dessinent",
      "longueurs : %d puis %d" % (len(planche), len(refaite)))

    conv = pg.evaluate("""(jour) => {
      const a = E.tenuesPassees.find(x => x.tenue.date === jour);
      return avecLaTenuePassee(a, () => convocation()); }""", JOUR)
    v(JOUR.split('-')[2].lstrip('0') in conv,
      "sa convocation aussi porte SA date, non celle de la tenue en cours",
      conv[:200])
    emarg = pg.evaluate("""(jour) => {
      const a = E.tenuesPassees.find(x => x.tenue.date === jour);
      return avecLaTenuePassee(a, () => emargement()); }""", JOUR)
    v(nomVisiteur in emarg, "et son emargement porte les Visiteurs de ce soir-la")

    # ══ 4. L'ATELIER EST REMIS COMME IL ETAIT ═══════════════════════
    # Dessiner une tenue passee remet l'Atelier dans l'etat de ce
    # soir-la. S'il y restait, la Secretaire travaillerait sur une
    # tenue d'il y a six mois sans le savoir.
    v(pg.evaluate("E.tenue.date") == "2027-01-11",
      "APRES AVOIR DESSINE UNE TENUE PASSEE, L'ATELIER EST REVENU A LA SIENNE",
      pg.evaluate("E.tenue.date"))
    v(pg.evaluate("Object.keys(E.presences).length") == 0,
      "et ses cases sont restees blanches", pg.evaluate("E.presences"))
    v(pg.evaluate("E.visiteurs.length") > 0 and
      pg.evaluate("E.visiteurs.every(x => !x.presentTenue)"),
      "et le carnet des Visiteurs est celui de l'Atelier, non celui de l'archive",
      pg.evaluate("E.visiteurs.map(x => [x.nom, x.presentTenue])"))

    # Et il revient meme si le dessin leve : sans cela, une tenue
    # d'il y a six mois resterait a l'ecran.
    v(pg.evaluate("""() => {
        const avant = E.tenue.date;
        try { avecLaTenuePassee(E.tenuesPassees[0], () => { throw new Error('x'); }); }
        catch (err) {}
        return E.tenue.date === avant; }"""),
      "MEME SI LE DESSIN ECHOUE : l'Atelier ne reste pas fige sur une "
      "tenue d'il y a six mois")

    # ══ 5. CORRIGER UNE DATE NE FAIT PAS UNE TENUE FANTOME ══════════
    combien = pg.evaluate("(E.tenuesPassees||[]).length")
    pg.click("#t-convoc"); pg.wait_for_timeout(700)
    pg.fill("[data-t='date']", "2027-01-18")
    pg.wait_for_timeout(1500)
    v(pg.evaluate("(E.tenuesPassees||[]).length") == combien,
      "CORRIGER UNE DATE SAISIE DE TRAVERS NE LAISSE PAS UNE TENUE VIDE A "
      "L'ARCHIVE : on ne classe que ce qui porte une trace",
      pg.evaluate("(E.tenuesPassees||[]).map(a => a.tenue.date)"))

    # ══ 6. CLASSER DEUX FOIS LA MEME TENUE NE FAIT PAS DEUX LIGNES ══
    pg.evaluate("""(jour) => { E.tenue.date = jour; E.convoquee = true;
      E.presences[convocables()[0].id] = 'present'; garder(); }""", JOUR)
    pg.wait_for_timeout(1200)
    pg.fill("[data-t='date']", "2027-02-08")
    pg.wait_for_timeout(1500)
    dates = pg.evaluate("(E.tenuesPassees||[]).map(a => a.tenue.date)")
    v(dates.count(JOUR) == 1,
      "ON REVIENT SUR UNE DATE, ON SE RAVISE : l'archive n'en porte "
      "toujours qu'une ligne", dates)

    # ══ 7. LE REGISTRE EN LIGNE LES PORTE AUSSI ═════════════════════
    # Une archive qui ne vit que dans un navigateur n'est pas une
    # archive : c'est une copie en sursis.
    pg.wait_for_timeout(1500)
    auServeur = pg.evaluate("""async () => {
      const r = await fetch('/api/etat', { credentials: 'same-origin' });
      const c = await r.json();
      return (c.donnees.tenuesPassees || []).map(a => a.tenue.date); }""")
    v(JOUR in auServeur,
      "LES TENUES CLASSEES SONT AU REGISTRE DE L'ATELIER, non dans le seul "
      "navigateur de la Secretaire", auServeur)

    # ══ 8. LE BOUTON DEMANDE : ENREGISTRER LES VISITEURS ════════════
    pg.click("#t-visiteurs"); pg.wait_for_timeout(800)
    v(pg.locator("#vis-pousser").count() == 1,
      "le carnet porte le bouton « Enregistrer les visiteurs pour tous »")
    d.clear()
    pg.click("#vis-pousser"); pg.wait_for_timeout(2500)
    dit = " ".join(d)
    combienVis = pg.evaluate("E.visiteurs.length")
    v(str(combienVis) in dit,
      "IL DIT COMBIEN DE VISITEURS SONT AU REGISTRE", dit[:260])
    v("relire" in dit or "relu" in dit,
      "ET QU'IL EST ALLE VERIFIER : une promesse qu'on peut verifier n'est "
      "plus une promesse", dit[:260])

    v(not e, "aucune erreur JavaScript", e)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
raise SystemExit(1 if ko else 0)
