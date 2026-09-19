# L'EPREUVE DE LA LECTURE D'UNE CONVOCATION
#
#   node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
#   node loge/serveur/faux-page.mjs    > /tmp/page-epreuve.html
#   export RBI_PAGE=/tmp/page-epreuve.html
#   RBI_PORT=8803 RBI_LECTURE=1 node loge/serveur/faux-serveur.mjs &   # cle posee
#   RBI_PORT=8804                node loge/serveur/faux-serveur.mjs &   # sans cle
#   RBI_PORT=8805 RBI_LECTURE=1 RBI_LECTURE_ECHEC=1 \
#     node loge/serveur/faux-serveur.mjs &                              # cle refusee
#   python3 loge/serveur/essai-lecture.py
#
# AUCUNE LECTURE NE PART VERS ANTHROPIC PENDANT CETTE EPREUVE. L'appel
# est intercepte par le faux serveur, qui garde ce qui LUI AURAIT ete
# remis : l'image, le modele, le schema. C'est cela qu'on verifie.
#
# CE QUI COMPTE LE PLUS ICI : LA CLE NE QUITTE JAMAIS LE SERVEUR. Une
# clé posee dans la page serait lisible par quiconque ouvre le
# programme — et facturee a l'Atelier jusqu'a ce qu'on s'en apercoive.
from playwright.sync_api import sync_playwright
import base64, os, pathlib, json

AVEC   = os.environ.get("RBI_URL_AVEC",   "http://127.0.0.1:8803/")
SANS   = os.environ.get("RBI_URL_SANS",   "http://127.0.0.1:8804/")
REFUS  = os.environ.get("RBI_URL_REFUS",  "http://127.0.0.1:8805/")
CLE    = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []


def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:240]}")
    if not c:
        ko.append(n)


# un PDF de scan : une image JPEG enveloppee, comme ceux qu'on recoit
JPG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
    "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==")
PDF = "/tmp/epreuve-convocation-scan.pdf"
pathlib.Path(PDF).write_bytes(b"%PDF-1.4\n% scan\n" + JPG + b"\n%%EOF\n")


def entrer(pg, url):
    pg.goto(url); pg.wait_for_timeout(900)
    pg.fill("#porte-mdp", CLE); pg.click("#porte-form button[type=submit]")
    pg.wait_for_timeout(1800)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    # == 1. LA CLE POSEE : LA CONVOCATION SE LIT ====================
    c1 = b.new_context(); A = c1.new_page()
    eA = []; A.on("pageerror", lambda e: eA.append(str(e)))
    dA = []; A.on("dialog", lambda d: (dA.append(d.message), d.accept()))
    entrer(A, AVEC)
    v(A.evaluate("""async () => {
        const r = await fetch('/api/lire'); return (await r.json()).configure; }"""),
      "la route dit qu'elle est servie AVANT qu'on propose un bouton")

    A.click("#t-amies"); A.wait_for_timeout(700)
    A.set_input_files("#fichier-amie-conv", PDF); A.wait_for_timeout(6000)
    lu = A.evaluate("""() => { const x = (E.amies||[]).find(y => y.id === E.amieOuverte);
      return x ? { nom: x.nom, orient: x.orient, temple: x.temple,
                   ville: x.ville, courriel: x.contactEmail,
                   conv: (x.convocations||[])[0] || null } : null; }""")
    v(lu and lu.get("nom") == "Les Ecossais de la Sainte Baume",
      "UNE CONVOCATION SCANNEE EN PDF SE LIT, et la Loge se remplit seule", lu)
    v(lu and lu.get("orient") == "Saint Maximin",
      "l'Orient est separe du nom, comme la consigne l'exige", lu)
    v(lu and lu.get("courriel") == "secretariat@ecossais.test",
      "LE COURRIEL DE CONTACT — un des quatre essentiels", lu)
    c = (lu or {}).get("conv") or {}
    v(c.get("date") == "2027-05-12" and c.get("heure") == "20:00",
      "LA DATE ET L'HEURE — les deux autres", c)
    v(c.get("degre") == 3 or c.get("degre") == 1,
      "et le degre des travaux", c.get("degre"))
    v(A.evaluate("prochainesVisites().some(x => x.c.date === '2027-05-12')"),
      "ET LA TENUE ENTRE A L'AGENDA DES VISITES, sans une saisie")
    v(any("RELISEZ" in d for d in dA),
      "on rappelle de RELIRE : une lecture automatique se trompe", dA[-1:])

    # == LA CONSIGNE DIT LE CAS QU'ON A VU SE TROMPER ===============
    # Sur la premiere convocation lue en service — R. Loge BASTET n°901
    # — le modele a range sous le Secretaire un numero qui etait celui
    # d'une Soeur chargee des repas : « reserver par SMS aupres de notre
    # Soeur Marie au 06 76 00 61 66 ». Il a vu un numero, il a vu un
    # contact, il les a maries. Un champ vide se remplit d'un coup de
    # telephone ; un mauvais numero se decouvre le soir de la tenue.
    consigne = A.evaluate("""async () => {
      const r = await fetch('/__lectures'); const l = await r.json();
      const c = l[0].corps.messages[0].content.find(x => x.type === 'text');
      return c ? c.text : ''; }""")
    v("Sœur Marie" in consigne or "Soeur Marie" in consigne,
      "LA CONSIGNE PORTE LE CAS REEL QU'ON A VU SE TROMPER, non une "
      "recommandation en l'air", consigne[-400:])
    # le texte est replie sur plusieurs lignes : on cherche un fragment
    # qui n'enjambe pas une coupure
    v("donne, non au secrétariat" in consigne,
      "et la regle qui en sort : un numero appartient a qui le donne",
      consigne[-400:])
    v("reste null" in consigne,
      "avec le refuge : dans le doute, on ne remplit pas", consigne[-300:])

    # == 2. LA CLE NE QUITTE PAS LE SERVEUR =========================
    envoye = A.evaluate("""async () => {
      const r = await fetch('/__lectures'); return await r.json(); }""")
    v(len(envoye) >= 1, "le service a bien ete appele", len(envoye))
    if envoye:
        v(envoye[0].get("cle") == "cle-epreuve-sans-valeur",
          "LA CLE VOYAGE DU SERVEUR AU SERVICE, jamais par la page",
          envoye[0].get("cle"))
        corps = envoye[0].get("corps") or {}
        v(corps.get("model") == "claude-opus-5",
          "le modele est celui qu'on a choisi", corps.get("model"))
        bl = (corps.get("messages") or [{}])[0].get("content") or []
        v(any(x.get("type") == "image" for x in bl),
          "l'image part bien avec la consigne", [x.get("type") for x in bl])
        v(((corps.get("output_config") or {}).get("format") or {}).get("type")
          == "json_schema",
          "ET UN SCHEMA FIXE : ce qui n'est pas une cle attendue n'entre pas",
          corps.get("output_config"))

    # la page, elle, n'a jamais vu la cle
    pageCle = A.evaluate("""() => {
      const t = document.documentElement.innerHTML;
      return t.includes('cle-epreuve-sans-valeur') ||
             t.includes('CLE_ANTHROPIC') || t.includes('sk-ant'); }""")
    v(pageCle is False,
      "ET LA PAGE NE LA PORTE NULLE PART : ni dans le texte, ni dans un champ")
    A.close(); c1.close()

    # == 3. SANS CLE : ON LE DIT, ET ON DIT QUOI ====================
    # « Elle fonctionne depuis la page en ligne » disait-on — a quelqu'un
    # QUI EST sur la page en ligne. On l'envoyait chercher la ou il est.
    c2 = b.new_context(); S = c2.new_page()
    eS = []; S.on("pageerror", lambda e: eS.append(str(e)))
    dS = []; S.on("dialog", lambda d: (dS.append(d.message), d.accept()))
    entrer(S, SANS)
    v(S.evaluate("""async () => {
        const r = await fetch('/api/lire'); return (await r.json()).configure; }""")
      is False, "sans cle, la route le dit")
    S.click("#t-amies"); S.wait_for_timeout(700)
    dS.clear()
    S.set_input_files("#fichier-amie-conv", PDF); S.wait_for_timeout(4000)
    dit = " ".join(dS)
    v("clé du service de lecture" in dit,
      "ON NOMME CE QUI MANQUE : la cle, non « ce n'est pas disponible »",
      dit[:220])
    v("en ligne, pas depuis le fichier" not in dit,
      "et l'on cesse d'envoyer chercher la ou l'on est deja", dit[:220])
    v(S.evaluate("""() => { const x = (E.amies||[]).find(y => y.id === E.amieOuverte);
        return !!(x && (x.convocations||[])[0] && x.convocations[0].piece); }"""),
      "la piece reste attachee : rien n'est perdu, il reste a saisir")
    S.close(); c2.close()

    # == 4. LA CLE REFUSEE : LA RAISON TELLE QUE DONNEE =============
    c3 = b.new_context(); R = c3.new_page()
    eR = []; R.on("pageerror", lambda e: eR.append(str(e)))
    dR = []; R.on("dialog", lambda d: (dR.append(d.message), d.accept()))
    entrer(R, REFUS)
    R.click("#t-amies"); R.wait_for_timeout(700)
    dR.clear()
    R.set_input_files("#fichier-amie-conv", PDF); R.wait_for_timeout(5000)
    ditR = " ".join(dR)
    v("refusé" in ditR and "cle refusee" in ditR,
      "LE REFUS EST DIT AVEC LA RAISON DU SERVICE, non une invention",
      ditR[:220])
    R.close(); c3.close()

    v(not eA and not eS and not eR, "aucune erreur JavaScript", eA + eS + eR)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
