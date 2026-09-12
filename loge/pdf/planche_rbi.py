# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  RITE BRITH ISRAËL — génération de la planche à tracer en PDF
  ReportLab. Voie serveur, complémentaire du gabarit HTML.

  Deux difficultés résolues ici, et vérifiées par extraction du PDF
  produit — non par supposition :

  1. LES POINTS MAÇONNIQUES. Le caractère ∴ (U+2234) passe dans les
     polices intégrées de ReportLab. Aucune précaution à prendre.

  2. L'HÉBREU NE PASSE PAS. Avec Helvetica, « ברית ישראל » sort en
     carrés noirs : les polices intégrées sont latines. Il faut une
     police qui porte l'alphabet hébreu — DejaVu Sans le fait — ET
     inverser la chaîne avant de la passer, parce que ReportLab dessine
     les glyphes de gauche à droite sans connaître l'écriture de droite
     à gauche. D'où hebreu() ci-dessous.

  ► CETTE INVERSION NE VAUT QUE POUR DES CHAÎNES PUREMENT HÉBRAÏQUES.
    Un mélange d'hébreu et de chiffres sortirait faux. Les quelques
    formules du Rite étant fixes et connues, cela suffit ; un texte
    hébreu libre demanderait une vraie mise en ordre bidirectionnelle.
═══════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, Image, KeepTogether)

ICI = Path(__file__).resolve().parent
ASSETS = ICI.parent / "assets"

# ── La charte, reprise de charte-rbi.css ───────────────────────────
OR        = colors.HexColor("#C9A84C")
OR_SOMBRE = colors.HexColor("#9A7535")
ENCRE     = colors.HexColor("#14110C")
ENCRE_2   = colors.HexColor("#5C5346")

# ── Les polices ────────────────────────────────────────────────────
# Times pour le corps : c'est la plus proche d'EB Garamond parmi les
# polices intégrées. DejaVu uniquement là où l'hébreu l'exige.
CORPS, CORPS_GRAS, CORPS_ITAL = "Times-Roman", "Times-Bold", "Times-Italic"
HEB = "DejaVuHebreu"
_CHEMIN_HEB = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def enregistrer_polices():
    """Sans police hébraïque, on le dit plutôt que d'imprimer des carrés."""
    if _CHEMIN_HEB.exists():
        pdfmetrics.registerFont(TTFont(HEB, str(_CHEMIN_HEB)))
        return True
    return False


def hebreu(texte):
    """L'hébreu s'écrit de droite à gauche, ReportLab dessine de gauche
    à droite : on lui présente la chaîne à l'envers pour qu'elle
    s'affiche à l'endroit."""
    return texte[::-1]


# ── Les styles ─────────────────────────────────────────────────────
def styles(avec_hebreu):
    police_heb = HEB if avec_hebreu else CORPS
    return {
        "formule": ParagraphStyle("formule", fontName=police_heb, fontSize=8.5,
                                  leading=11, alignment=TA_CENTER, textColor=OR_SOMBRE),
        "conseil": ParagraphStyle("conseil", fontName=CORPS_GRAS, fontSize=10,
                                  leading=13, alignment=TA_CENTER, textColor=ENCRE),
        "qualite": ParagraphStyle("qualite", fontName=CORPS, fontSize=7.5,
                                  leading=10, alignment=TA_CENTER, textColor=ENCRE_2),
        "atelier": ParagraphStyle("atelier", fontName=police_heb, fontSize=10.5,
                                  leading=14, alignment=TA_CENTER, textColor=ENCRE),
        "atelier_latin": ParagraphStyle("atelier_latin", fontName=CORPS_GRAS, fontSize=10.5,
                                        leading=14, alignment=TA_CENTER, textColor=ENCRE),
        "orient":  ParagraphStyle("orient", fontName=CORPS_ITAL, fontSize=8.5,
                                  leading=11, alignment=TA_CENTER, textColor=ENCRE_2),
        "titre":   ParagraphStyle("titre", fontName=CORPS_GRAS, fontSize=15,
                                  leading=19, alignment=TA_CENTER, spaceBefore=4*mm,
                                  spaceAfter=7*mm, textColor=ENCRE),
        "rubrique": ParagraphStyle("rubrique", fontName=CORPS_GRAS, fontSize=10,
                                   leading=13, spaceBefore=6*mm, spaceAfter=2.5*mm,
                                   textColor=ENCRE),
        "corps":   ParagraphStyle("corps", fontName=CORPS, fontSize=11.5, leading=16,
                                  alignment=TA_JUSTIFY, spaceAfter=3.6*mm, textColor=ENCRE),
        "liste":   ParagraphStyle("liste", fontName=CORPS, fontSize=11, leading=15,
                                  leftIndent=5*mm, firstLineIndent=-5*mm,
                                  spaceAfter=1.6*mm, textColor=ENCRE),
        "mention": ParagraphStyle("mention", fontName=CORPS_ITAL, fontSize=9.5,
                                  leading=13, textColor=ENCRE_2),
    }


# ── L'en-tête ──────────────────────────────────────────────────────
def entete(S, loge, avec_hebreu):
    """Sceau du Suprême Conseil à gauche, sceau de l'Atelier à droite,
    la qualité entre les deux — la disposition de la charte."""
    def sceau(nom, largeur=20 * mm):
        f = ASSETS / nom
        return Image(str(f), width=largeur, height=largeur) if f.exists() else ""

    # ► UN PARAGRAPHE NE MÊLE JAMAIS LATIN ET HÉBREU.
    #   Vérifié en rendant puis en extrayant le PDF : un paragraphe qui
    #   contient les deux écritures perd sa partie latine —
    #   « A∴L∴G∴ — בס״ד » ressort réduit à « בס״ד ». Chaque écriture a
    #   donc sa ligne. Ce n'est pas un contournement : c'est aussi ce
    #   que fait votre papier à en-tête.
    centre = [
        Paragraph("A∴L∴G∴D∴G∴A∴D∴L∴U∴", S["formule"]),
    ]
    if avec_hebreu:
        centre.append(Paragraph(hebreu("בס״ד"), S["formule"]))
    centre += [
        Paragraph("Suprême Conseil Mondial du Rite BRITH ISRAËL", S["conseil"]),
        Paragraph("FRANCS-MAÇONS DE TRADITION HÉBRAÏQUE &amp; KABBALISTIQUE", S["qualite"]),
    ]
    if avec_hebreu:
        centre.append(Paragraph(hebreu("חי חי חי ויקיים"), S["formule"]))
    centre += [
        Paragraph("HAI HAI HAI VEQAYAM", S["formule"]),
        Spacer(1, 2.5 * mm),
        Paragraph(f"R∴L∴ {loge['nom']} &nbsp;n°{loge['numero']}", S["atelier_latin"]),
    ]
    if avec_hebreu and loge.get("nom_hebreu"):
        centre.append(Paragraph(hebreu(loge["nom_hebreu"]), S["atelier"]))
    centre.append(Paragraph(loge["mention"], S["orient"]))

    t = Table([[sceau("sceau-rbi.png"), centre, sceau("logo-rl-bereshit.png")]],
              colWidths=[24 * mm, None, 24 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, OR),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    return t


def ligne_membre(m):
    """« — Jean-Michel RAUX, 32° du Rite Brith Israël, Vénérable Maître. »
    Une qualité absente ne laisse pas de virgule orpheline."""
    bouts = [m["nom"]]
    if m.get("qualite"):
        bouts.append(m["qualite"])
    if m.get("office"):
        bouts.append(f"<i>{m['office']}</i>")
    return "— " + ", ".join(bouts) + "."


def construire(donnees, chemin):
    """Produit la planche. « donnees » suit le même contrat que le
    gabarit HTML : ce qui n'est pas fourni n'est pas inventé."""
    avec_hebreu = enregistrer_polices()
    S = styles(avec_hebreu)
    D, L = donnees, donnees["loge"]
    doc = SimpleDocTemplate(str(chemin), pagesize=A4, title="Planche à tracer",
                            author="Rite Brith Israël",
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm)
    r = []
    r.append(entete(S, L, avec_hebreu))
    r.append(Paragraph(f"Planche à Tracer du {D['date_longue']}<br/>"
                       f"{D.get('date_hebraique') or D['avl']} A∴V∴L∴", S["titre"]))

    # Les deux dates : celle du calendrier hébraïque et celle de l'ère
    # vulgaire. L'année hébraïque tourne à Roch Hachana, non au 1er
    # janvier — d'où un vrai calendrier, et non une addition.
    heb = D.get("date_hebraique")
    ouverture = (f"Dans un lieu très éclairé, très pur, le {heb} de l'An de Vraie Lumière, "
                 f"correspondant au {D['date_longue']} de l'ère vulgaire, "
                 if heb else
                 f"Dans un lieu très éclairé, très pur, le {D['date_longue']}, ")
    r.append(Paragraph(
        ouverture + f"s'est réunie la R∴L∴ {L['nom']} n°{L['numero']}, "
        f"à l'O∴ de {L['orient']}, au {D['lieu']}.", S["corps"]))

    r.append(Paragraph("Sont présents les SS∴ et FF∴ Membres de la Loge", S["rubrique"]))
    for m in D["presents"]:
        r.append(Paragraph(ligne_membre(m), S["liste"]))

    r.append(Paragraph("Se sont fait excuser", S["rubrique"]))
    if D["excuses"]:
        for m in D["excuses"]:
            r.append(Paragraph(ligne_membre(m), S["liste"]))
    else:
        r.append(Paragraph("Aucun.", S["mention"]))

    if D.get("visiteurs"):
        r.append(Paragraph("Les SS∴ et FF∴ Visiteurs", S["rubrique"]))
        for v in D["visiteurs"]:
            r.append(Paragraph(ligne_membre(v), S["liste"]))

    r.append(Spacer(1, 3 * mm))
    r.append(Paragraph(
        f"Après une allocution de bienvenue, le VM∴ {D['venerable']} ouvre les travaux sous "
        f"les auspices du Suprême Conseil Mondial du Rite Brith Israël, au {D['degre_ordinal']} "
        f"degré {D['degre_de']} du Rite Brith Israël.", S["corps"]))

    for p in D["paragraphes"]:
        r.append(Paragraph(f"<b>{p['intitule']}</b>", S["rubrique"]))
        r.append(Paragraph(p["texte"] or
                 "<i>Le récit de ce point — écrit par le Secrétaire, par personne d'autre.</i>",
                 S["corps"]))

    r.append(Paragraph(
        "Les colonnes ayant résonné de ces précieuses paroles, l'ordre du jour étant épuisé, "
        "et tout ayant été conforme au Rite, le VM∴ procède à la clôture des travaux.", S["corps"]))
    r.append(Paragraph(
        f"S'ensuit une chaleureuse et fraternelle chaîne d'union ; le sac aux propositions "
        f"{D['sac']} ; le Tronc de la Veuve est alourdi d'une pierre plate de {D['tronc']}. "
        f"Le montant sera confié à la garde de notre {D['tronc_confie_a']}.", S["corps"]))
    r.append(Paragraph(
        f"Les Officiers ayant éteint leurs plateaux, les SS∴ et FF∴ de la R∴L∴ {L['nom']}, "
        f"ayant mérité le repos, se retirent en jurant de garder le silence sur les travaux "
        f"venant de se dérouler, et, ayant à cœur de continuer à œuvrer à l'extérieur du Temple "
        f"pour unir ce qui est épars, se réuniront le {D['prochaine']} pour leur prochaine tenue.",
        S["corps"]))

    r.append(Spacer(1, 4 * mm))
    r.append(Paragraph(
        f"Procès-verbal rédigé par {D['redacteur']}, par rotation entre les membres présents, "
        f"sous la responsabilité du Vénérable Maître, et lu et approuvé à l'ouverture de la "
        f"tenue suivante.", S["mention"]))

    signatures = [[Paragraph(f"<b>{o}</b><br/><i>{n}</i>", S["liste"])] for o, n in D["signatures"]]
    for bloc in signatures:
        r.append(KeepTogether([Spacer(1, 10 * mm), bloc[0],
                               Table([[""]], colWidths=[62 * mm], rowHeights=[9 * mm],
                                     style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4,
                                                        colors.HexColor("#A89A76"))]))]))
    doc.build(r)
    return chemin, avec_hebreu
