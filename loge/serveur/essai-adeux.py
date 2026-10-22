# L'EPREUVE DU TRAVAIL A DEUX
#
#   RBI_PAGE=/tmp/page-epreuve.html RBI_PORT=8811 \
#     node loge/serveur/faux-serveur.mjs &
#   python3 loge/serveur/essai-adeux.py
#
# CE QU'ON EPROUVE, ET POURQUOI C'EST LE COEUR. Le registre s'ecrivait
# en bloc : chaque enregistrement remettait TOUT le document. Si
# quelqu'un avait ecrit entre-temps, le serveur refusait et le
# programme posait cette question :
#
#   « Quelqu'un d'autre a enregistre pendant que vous travailliez.
#     OK : je reprends la version du registre — ce qui n'est que sur
#     cet appareil sera perdu. »
#
# Autrement dit : a deux, l'un des deux perdait son travail. C'est
# exactement ce que ce serveur existait pour empecher, et c'est ce
# qu'il faisait. On eprouve donc le cas reel : la Soeur Secretaire note
# un telephone pendant que le Tresorier saisit un reglement.
from playwright.sync_api import sync_playwright
import os

U = os.environ.get("RBI_URL", "http://127.0.0.1:8811/")
TABLEAU = os.environ.get("RBI_TABLEAU", "/tmp/tableau.json")
CLE = os.environ.get("RBI_CLE", "cleSecretariatEpreuve")
ko = []

def v(c, n, d=''):
    print(f"  {'OK ' if c else 'NON'}  {n}{'' if c else '  <- ' + str(d)[:280]}")
    if not c: ko.append(n)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    def ouvrir():
        c = b.new_context(); p = c.new_page()
        e = []; p.on("pageerror", lambda x: e.append(str(x)))
        d = []; p.on("dialog", lambda x: (d.append(x.message), x.accept()))
        p.goto(U); p.wait_for_timeout(800)
        p.fill("#porte-mdp", CLE); p.click("#porte-form button[type=submit]")
        p.wait_for_timeout(2400)
        return c, p, e, d

    # ══ LA SECRETAIRE OUVRE SON ECRAN ET POSE LE TABLEAU ════════════
    cA, A, eA, dA = ouvrir()
    A.set_input_files("#fichier-sauvegarde", TABLEAU); A.wait_for_timeout(2800)
    vA = A.evaluate("SERVEUR.version")
    v(vA > 0, "le registre est en ligne", vA)
    v(A.evaluate("SERVEUR.socle !== null"),
      "ET LE PROGRAMME GARDE SON SOCLE : c'est lui qui permettra au serveur "
      "de savoir qui a change quoi")

    # ══ LE TRESORIER OUVRE LE SIEN, SUR LE MEME ETAT ════════════════
    cB, B, eB, dB = ouvrir()
    B.wait_for_timeout(1500)
    v(B.evaluate("E.membres.length") == A.evaluate("E.membres.length"),
      "les deux ecrans partent du meme Tableau",
      (A.evaluate("E.membres.length"), B.evaluate("E.membres.length")))
    ID = A.evaluate("E.membres[0].id")

    # ══ LA SECRETAIRE NOTE UN TELEPHONE ═════════════════════════════
    dA.clear()
    A.evaluate("(id) => { const m = E.membres.find(x => x.id === id); "
               "m.tel = '06 11 22 33 44'; garder(); }", ID)
    A.wait_for_timeout(2500)
    v(A.evaluate("SERVEUR.version") > vA, "son enregistrement est passe",
      A.evaluate("SERVEUR.version"))

    # ══ ET LE TRESORIER, QUI N'A PAS RECHARGE, SAISIT UN REGLEMENT ══
    # Son programme se fonde encore sur l'etat d'AVANT. C'est ici que
    # l'un des deux perdait son travail.
    # PERIME : son programme se fonde sur une version que le registre a
    # deja depassee. C'est la condition exacte ou l'on perdait du
    # travail, et on la verifie au lieu de la supposer.
    courante = B.evaluate("async () => (await (await fetch('/api/etat', { credentials: 'same-origin' })).json()).version")
    v(B.evaluate("SERVEUR.version") < courante,
      "LE TRESORIER SE FONDE SUR UN ETAT DEJA DEPASSE : c'est le cas reel, "
      "celui ou l'un des deux perdait son travail",
      (B.evaluate("SERVEUR.version"), courante))
    dB.clear()
    B.evaluate("(id) => { const m = E.membres.find(x => x.id === id); "
               "m.regle = 480; garder(); }", ID)
    B.wait_for_timeout(3000)

    v(not dB, "AUCUNE QUESTION NE LUI EST POSEE : on ne lui demande plus de "
              "choisir entre son travail et celui de l'autre", dB)

    # ══ LES DEUX TRAVAUX TIENNENT ═══════════════════════════════════
    chez_lui = B.evaluate("(id) => { const m = E.membres.find(x => x.id === id); "
                          "return { tel: m.tel, regle: m.regle }; }", ID)
    v(chez_lui.get("regle") == 480,
      "son reglement est enregistre", chez_lui)
    v(chez_lui.get("tel") == "06 11 22 33 44",
      "ET LE TELEPHONE DE LA SECRETAIRE EST APPARU SUR SON ECRAN, sans qu'il "
      "recharge et sans qu'on lui demande rien", chez_lui)

    registre = B.evaluate("""async () => {
      const r = await fetch('/api/etat', { credentials: 'same-origin' });
      const c = await r.json();
      return { version: c.version, membres: c.donnees.membres }; }""")
    m = [x for x in registre["membres"] if x["id"] == ID][0]
    v(m.get("tel") == "06 11 22 33 44" and m.get("regle") == 480,
      "ET LE REGISTRE PORTE LES DEUX : rien n'a ete perdu", m)

    # ══ ET LA SECRETAIRE VOIT LE REGLEMENT ARRIVER ══════════════════
    # Sans cela, la fusion ne servirait qu'a celui qui ecrit le dernier :
    # l'autre resterait sur son ecran d'avant, et croirait que rien
    # n'a ete fait.
    avant = A.evaluate("(id) => E.membres.find(x => x.id === id).regle", ID)
    v(avant != 480, "elle ne l'a pas encore vu", avant)
    A.evaluate("async () => { await releverRegistre(); }")
    A.wait_for_timeout(1500)
    apres = A.evaluate("(id) => E.membres.find(x => x.id === id).regle", ID)
    v(apres == 480,
      "LE REGLEMENT DU TRESORIER APPARAIT SUR SON ECRAN TOUT SEUL", apres)
    v(A.evaluate("(id) => E.membres.find(x => x.id === id).tel", ID)
      == "06 11 22 33 44", "et son propre travail n'a pas ete ecrase")

    # ══ CE QU'ON NE SAIT PAS FUSIONNER SE DIT ═══════════════════════
    # Quand les DEUX ont change LE MEME champ, aucune regle ne devine
    # lequel a raison. Le dernier qui ecrit l'emporte — et c'est le
    # seul endroit ou quelque chose se perd, donc le seul qu'on
    # consigne.
    A.evaluate("() => { E.tenue.heureOuv = '20:00'; garder(); }")
    A.wait_for_timeout(2500)
    jAvant = B.evaluate("(E.journal || []).length")
    dB.clear()
    B.evaluate("() => { E.tenue.heureOuv = '19:00'; garder(); }")
    B.wait_for_timeout(3000)
    v(B.evaluate("E.tenue.heureOuv") == '19:00',
      "sur le meme champ, le dernier qui ecrit l'emporte",
      B.evaluate("E.tenue.heureOuv"))
    v(B.evaluate("(E.journal || []).length") > jAvant,
      "ET L'ARBITRAGE EST PORTE AU JOURNAL : un arbitrage qu'on ne voit pas "
      "se decouvre trop tard",
      B.evaluate("(E.journal || []).slice(0, 2)"))
    v("tranché" in str(B.evaluate("(E.journal || [])[0]")),
      "le journal dit ce qui a ete tranche", B.evaluate("(E.journal || [])[0]"))
    v(not dB, "et cela n'interrompt personne : aucune boite de dialogue", dB)

    # ══ ON NE REDESSINE PAS SOUS LES DOIGTS DE QUELQU'UN ════════════
    # Redessiner pendant qu'une Soeur tape dans une case lui enleve le
    # curseur et avale sa frappe.
    #
    # Le foyer d'un champ ne survit pas au passage d'une page a l'autre
    # dans un meme navigateur : on eprouve donc LA GARDE elle-meme, en
    # la forcant, plutot qu'un foyer que le banc d'essai ne sait pas
    # tenir. Que la garde reconnaisse un champ au foyer se verifie a
    # part, juste au-dessus.
    A.click("#t-tableau"); A.wait_for_timeout(600)
    A.evaluate("() => { E.fiche = E.membres[0].id; courante = 'fiche'; dessiner(); }")
    A.wait_for_timeout(700)
    A.focus("#m-tel")
    v(A.evaluate("doigtsSurLeClavier()") is True,
      "LE PROGRAMME SAIT QU'UNE CASE A LE FOYER")
    A.evaluate("() => { document.activeElement && document.activeElement.blur(); }")
    A.wait_for_timeout(200)
    v(A.evaluate("doigtsSurLeClavier()") is False,
      "et qu'elle ne l'a plus", A.evaluate("doigtsSurLeClavier()"))

    B.evaluate("() => { E.tenue.adage = 'Un autre adage'; garder(); }")
    B.wait_for_timeout(2500)

    A.evaluate("() => { window.__vraieGarde = doigtsSurLeClavier;"
               " doigtsSurLeClavier = () => true; }")
    A.evaluate("async () => { await releverRegistre(); }")
    A.wait_for_timeout(1200)
    v(A.evaluate("E.tenue.adage") != 'Un autre adage',
      "ET TANT QU'ON TAPE, IL N'ADOPTE RIEN : vingt secondes ne pressent "
      "personne, une frappe avalee ne se rattrape pas",
      A.evaluate("E.tenue.adage"))

    A.evaluate("() => { doigtsSurLeClavier = window.__vraieGarde; }")
    A.evaluate("async () => { await releverRegistre(); }")
    A.wait_for_timeout(1200)
    v(A.evaluate("E.tenue.adage") == 'Un autre adage',
      "et des que les doigts sont leves, il reprend ce qui a change",
      A.evaluate("E.tenue.adage"))

    v(not eA, "aucune erreur JavaScript a l'ecran de la Secretaire", eA)
    v(not eB, "aucune erreur JavaScript a l'ecran du Tresorier", eB)
    b.close()

print(f"\n  {len(ko)} echec(s)" if ko else "\n  tout passe")
raise SystemExit(1 if ko else 0)
