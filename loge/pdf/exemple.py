# -*- coding: utf-8 -*-
"""Exemple d'appel : la tenue du 7 septembre 2026 de la R∴L∴ Bereshit."""
from pathlib import Path
from planche_rbi import construire

Q = lambda g: f"{g} du Rite Brith Israël"

DONNEES = {
    "loge": {"nom": "BERESHIT", "numero": "00", "nom_hebreu": "בראשית",
             "orient": "l'Alliance",
             "mention": "Loge Mère du Rite — Atelier Mixte à l'O∴ de l'Alliance"},
    "date_longue": "lundi 7 septembre 2026", "avl": 5786, "jour": 7, "mois": 7,
    "lieu": "Temple « Le Venaqui », à Ventabren",
    "degre_ordinal": "premier", "degre_de": "d'Apprenti Oved",
    "venerable": "TIF Jean-Michel RAUX",
    "presents": [
        {"nom": "TIF Mickaël DARMON", "qualite": Q("33°"), "office": "Souverain Grand Commandeur"},
        {"nom": "TIF Jean-Michel RAUX", "qualite": Q("32°"), "office": "Vénérable Maître"},
        {"nom": "TIS Martine HABERT", "qualite": Q("32°"), "office": "Premier Surveillant"},
        {"nom": "TIF Jean-Louis CARILLO", "qualite": Q("32°"), "office": "Second Surveillant"},
        {"nom": "TIF Didier BUHLER", "qualite": Q("32°")},
        {"nom": "TIS Valérie ROUME", "qualite": Q("32°")},
        {"nom": "F∴ Sam GASMI", "qualite": Q("Maître Adon")},
        {"nom": "F∴ Jean-Marc SAFFARO", "qualite": Q("Compagnon Boneh")},
    ],
    "excuses": [
        {"nom": "TIF Laurent NOTARIANNI", "qualite": Q("32°"), "office": "Membre d'honneur ad vitam"},
        {"nom": "TIF Philippe NAKACHE", "qualite": Q("Maître Adon"), "office": "réside en Nouvelle-Calédonie"},
    ],
    "visiteurs": [
        {"nom": "TIF Thierry HUGON", "qualite": "33ème, de l'Atelier de la FLTS",
         "office": "tuilé par le TIF Jean-Louis CARILLO"},
    ],
    "paragraphes": [
        {"intitule": "Quelques mots de bienvenue du Vénérable Maître", "texte": ""},
        {"intitule": "Cinq minutes de symbolisme — « L'initiation au Rite Brith Israël », "
                     "par le SGC∴ Mickaël DARMON", "texte": ""},
        {"intitule": "Cérémonie d'initiation de la Première Apprentie de l'Atelier", "texte": ""},
    ],
    "sac": "revient pur et sans attaches",
    "tronc": "87 kg 500",
    "tronc_confie_a": "F∴ Second Surveillant",
    "prochaine": "lundi 5 octobre 2026",
    "redacteur": "la TIS Valérie ROUME",
    "signatures": [("Le Vénérable Maître", "TIF Jean-Michel RAUX"),
                   ("Le Premier Surveillant", "TIS Martine HABERT"),
                   ("Le Second Surveillant", "TIF Jean-Louis CARILLO")],
}

if __name__ == "__main__":
    chemin, heb = construire(DONNEES, Path(__file__).parent / "planche-exemple.pdf")
    print("PDF produit :", chemin)
    print("hébreu imprimable :", "oui" if heb else "non — police absente, formules latines seules")
