/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — config.js
   
   ► C'EST ICI QUE TOUT SE MODIFIE ◄
   
   Textes, noms, liens, réponses de tuilage, PDFs, couleurs...
   Ne toucher ni index.html ni app.js sauf cas exceptionnel.
════════════════════════════════════════════════════════════════ */

var RBI_CONFIG = {

  /* ──────────────────────────────────────────────
     PAGE : NAVBAR
  ────────────────────────────────────────────── */
  navbar: {
    nom:    "BRITH ISRAËL®",
    hebrew: "ברית ישראל",
   liens: [
  { label: "Le Rite",          href: "#rite"   },
  { label: "Chefs de l'Ordre", href: "#chefs"  },
  { label: "Publications",     href: "#livres" },
  { label: "Traités",          href: "traites.html" },
  { label: "Devenir FM",       href: "devenir-fm.html", style: "cta" },
  { label: "Tuilage",          href: "#tuilage", style: "discret" },
  { label: "Espace Membres",   href: "espace-membres.html" },
  { label: "Contact",          href: "#contact" }
]
  },

  /* ──────────────────────────────────────────────
     PAGE : HERO (section d'accueil)
  ────────────────────────────────────────────── */
  hero: {
    bandeau:   "A∴L∴G∴G∴A∴D∴L'∴U∴ — ב∴ס∴ד∴",
    titre_fr:  "Rite Brith Israël®",
    titre_he:  "ברית ישראל",
    subtitle:  "Rite Maçonnique Historique d'inspiration Kabbalistique en 33 degrés.",
    subtitle2: "Alliance de Lumière entre les Peuples, fidélité à la Tradition Hébraïque, universalité de la Franc-Maçonnerie.",
    btn_decouvrir: "Découvrir le Rite",
    btn_rejoindre: "Devenir Franc-Maçon"
  },

  /* ──────────────────────────────────────────────
     PAGE : LE RITE
  ────────────────────────────────────────────── */
  rite: {
    titre: "Le Rite Brith Israël",
    intro: "Fondé par le T∴I∴F∴ Mickaël DARMON 33e, le Rite Brith Israël est un Rite Maçonnique Kabbalistique en 33 degrés puisant ses sources dans la Tradition Hébraïque, la Kabbale et la Franc-Maçonnerie universelle. Son nom honore la mémoire d'Israël DARMON, pilier spirituel et inspirateur du Rite.",
    cartes: [
      {
        icone: "✡",
        titre: "Tradition Hébraïque",
        texte: "Enraciné dans la sagesse millénaire de la Torah et de la Kabbale, le Rite transmet l'Alliance originelle entre l'Homme et le Divin."
      },
      {
        icone: "△",
        titre: "33 Degrés",
        texte: "Un parcours initiatique structuré en 33 degrés, des Loges de Perfection au Suprême Conseil, guidant le Frère vers la Lumière."
      },
      {
        icone: "☆",
        titre: "Alliance Universelle",
        texte: "Ouvert à tous les Frères réguliers, le Rite tisse des liens d'amitié et de fraternité avec les Obédiences du monde entier."
      }
    ]
  },

  /* ──────────────────────────────────────────────
     PAGE : CHEFS DE L'ORDRE
  ────────────────────────────────────────────── */
  chefs: {
    titre: "Chefs de l'Ordre",
    membres: [
      /* ── Souverain Grand Commandeur ── */
      {
        nom:    "Mickaël DARMON",
        grade:  "33°",
        titre:  "Souverain Grand Commandeur — T∴I∴F∴",
        role:   "Fondateur et Grand Maître",
        img_id: "photo-darmon",   // ID injecté par images.js
        rang:   "sgc"
      },
      /* ── Grands Maîtres Adjoints ── */
      {
        nom:    "Jean-Michel RAUX",
        grade:  "32°",
        titre:  "Grand Maître Adjoint",
        role:   "Lieutenant Souverain Grand Commandeur —  Grand Trésorier",
        img_id: "photo-raux",
        rang:   "gma"
      },
      {
        nom:    "Martine HABERT",
        grade:  "32°",
        titre:  "Grand Maître Adjoint",
        role:   " Grand Secrétaire",
        img_id: "photo-habert",
        rang:   "gma"
      },
      {
        nom:    "Jean-Louis CARILLO",
        grade:  "32°",
        titre:  "Grand Maître Adjoint",
        role:   "Grand Expert",
        img_id: "photo-carillo",
        rang:   "gma"
      },
      /* ── Adjoints au Grand Maître ── */
      {
        nom:    "Didier BUHLER",
        grade:  "32°",
        titre:  "Assistant Grand Maître",
        role:   " Grand Chancelier",
        img_id: "photo-buhler",
        rang:   "agm"
      },
      {
        nom:    "Laurent NOTARIANNI",
        grade:  "32°",
        titre:  "Assistant Grand Maître",
        role:   " Grand Orateur",
        img_id: "photo-notarianni",
        rang:   "agm"
      },
      {
        nom:    "Pierre JOURDAN",
        grade:  "32°",
        titre:  "Assistant Grand Maître",
        role:   " Grand Hospitalier",
        img_id: "photo-jourdan",
        rang:   "agm"
      }
    ]
  },

  /* ──────────────────────────────────────────────
     PAGE : LIVRES / PUBLICATIONS
  ────────────────────────────────────────────── */
  livres: {
    titre: "Publications",
    liste: [
      {
        img_id:   "book-alliance",
        titre:    "L'Alliance de Lumière",
        sous:     "Tome I — Rituel du Rite Brith Israël",
        desc:     "Le premier tome des rituels du Rite Brith Israël, publié aux éditions CoolLibri. Fondement doctrinal et initiatique du Rite.",
        placeholder: "L",
        liens: [
          { label: "CoolLibri", url: "https://www.coollibri.com/bibliotheque-en-ligne/mickael-darmon/brith-israel-lalliance-de-lumiere_1428718", style: "primary" }
        ]
      },
      {
        img_id:   "book-guide",
        titre:    "Guide de Survie pour Franc-Maçon Désemparé",
        sous:     "Mickaël DARMON — Amazon KDP",
        desc:     "Un guide pratique et humoristique pour naviguer dans le monde maçonnique, par le fondateur du Rite Brith Israël.",
        placeholder: "G",
        liens: [
          { label: "Amazon", url: "https://amzn.eu/d/03LwhX1a", style: "primary" }
        ]
      }
    ]
  },

  /* ──────────────────────────────────────────────
     PAGE : TUILAGE MAÇONNIQUE
     ► Modifier ici les questions et réponses ◄
  ────────────────────────────────────────────── */
  tuilage: {
    titre: "Tuilage Maçonnique",
    intro: "Frère, avant d'accéder aux documents réservés, veuillez répondre aux questions de tuilage.",
    max_essais: 3,           // Nombre d'essais par question
    questions: [
      {
        id:       "q1",
        texte:    "D'où venez-vous ?",
        // Toutes les réponses acceptées (insensible accents + casse)
        reponses: [
          "de saint jean",
          "saint jean",
          "du saint jean",
          "de chez saint jean",
          "loge de saint jean",
          "loge saint jean",
          "loge de st jean",
          "loge st jean",
          "de la loge saint jean",
          "de la loge st jean"
        ]
      },
      {
        id:       "q2",
        texte:    "Quel âge avez-vous ?",
        reponses: [
          "3 ans", "trois ans",
          "5 ans", "cinq ans",
          "7 ans", "sept ans",
          "3", "5", "7",
          "3 5 7", "3 5 et 7",
          "trois cinq sept",
          "trois cinq et sept",
          "7 ans et plus", "sept ans et plus",
          "7 et plus", "sept et plus",
          "plus de 7", "plus de sept",
          "3ans", "5ans", "7ans"
        ]
      }
    ],
    succes: {
      icone:    "✡",
      titre:    "Frère reconnu",
      message:  "M∴T∴C∴S∴ — Que la Lumière vous guide."
    },
    echec: {
      message: "Je ne saurais vous reconnaître, Profane."
    },
    // PDFs débloqués après tuilage réussi — src injecté par images.js
    pdfs: [
      { id: "pdf-btn-1", label: "Document Initiatique I"   },
      { id: "pdf-btn-2", label: "Document Initiatique II"  },
      { id: "pdf-btn-3", label: "Document Initiatique III" }
    ]
  },

  /* ──────────────────────────────────────────────
     PAGE : CONTACT
  ────────────────────────────────────────────── */
  contact: {
    titre:    "Contact",
    intro:    "Pour toute demande d'information ou d'affiliation :",
    email:    "contact.brith.israel@gmail.com",
    facebook: {
      label: "Facebook – Rite Brith Israël",
      url:   "https://www.facebook.com/profile.php?id=61586037824874"
    },
    traites: {
      label: "Traités & Obédiences alliées",
      url:   "traites.html"
    }
  },

  /* ──────────────────────────────────────────────
     FOOTER
  ────────────────────────────────────────────── */
  footer: {
    hebrew:  "ברית ישראל",
    ligne1:  "Suprême Conseil Mondial du Rite Brith Israël",
    ligne2:  "© 2025 Rite Brith Israël — Tous droits réservés"
  }

};
