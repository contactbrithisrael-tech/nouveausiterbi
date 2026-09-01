/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — config.js
   
   ► C'EST ICI QUE TOUT SE MODIFIE ◄
   
   Textes, noms, liens, réponses de tuilage, PDFs, couleurs...
   Ne toucher ni index.html ni app.js sauf cas exceptionnel.
════════════════════════════════════════════════════════════════ */

/* ──────────────────────────────────────────────
   AVATAR ANONYME
   Pour un Officier qui ne souhaite pas voir sa photo publiée.
   Ajouter « img_data: RBI_AVATAR_ANONYME » à sa fiche ci-dessous.
   Le SVG est écrit en clair : couleurs et tracé se modifient ici.
────────────────────────────────────────────── */
var RBI_AVATAR_ANONYME =
  "data:image/svg+xml;utf8," +
  "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E" +
  "%3Crect width='100' height='100' fill='%231a1a1a'/%3E" +
  "%3Ccircle cx='50' cy='37' r='15.5' fill='none' stroke='%23c9a84c' stroke-width='2.4' opacity='.55'/%3E" +
  "%3Cpath d='M21 87c0-16 13-29 29-29s29 13 29 29' fill='none' stroke='%23c9a84c' stroke-width='2.4' stroke-linecap='round' opacity='.55'/%3E" +
  "%3C/svg%3E";

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
  { label: "Légitimité",       href: "legitimite.html" },
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
    subtitle:  "Rite maçonnique d'inspiration kabbalistique, en 33 degrés.",
    subtitle2: "Une Alliance de Lumière entre les peuples : fidélité à la Tradition hébraïque, ouverture à la Franc-Maçonnerie universelle.",
    btn_decouvrir: "Découvrir le Rite",
    btn_rejoindre: "Devenir Franc-Maçon"
  },

  /* ──────────────────────────────────────────────
     PAGE : LE RITE
  ────────────────────────────────────────────── */
  rite: {
    titre: "Le Rite Brith Israël",
    intro: "Fondé en 2025 par Mickaël Darmon, 33e du Rite Écossais Ancien et Accepté, le Rite Brith Israël est un rite maçonnique d'inspiration kabbalistique en 33 degrés, qui puise ses sources dans la Tradition hébraïque, la Kabbale et la Franc-Maçonnerie universelle. Son nom honore la mémoire d'Israël Darmon, grand-père du fondateur et inspirateur du Rite. Son inspiration est hébraïque et kabbalistique ; elle n'est pas confessionnelle. Le Rite reprend la tradition primitive du Temple de Salomon, socle commun de toute la Franc-Maçonnerie, et ne demande à personne d'être juif ni de le devenir.",
    cartes: [
      {
        icone: "✡",
        titre: "Tradition Hébraïque, ouverte à tous",
        texte: "Le Rite lit le symbolisme maçonnique à sa source hébraïque et kabbalistique — un matériau millénaire dont rien n'a été inventé. Il n'est pas confessionnel et n'est réservé à aucune communauté : il accueille toutes celles et ceux qui cherchent, quelles que soient leur origine et leur religion."
      },
      {
        icone: "△",
        titre: "33 Degrés",
        texte: "Un parcours initiatique structuré en 33 degrés, des Loges symboliques aux Ateliers de perfection, que chaque Frère et chaque Sœur parcourt à son rythme."
      },
      {
        icone: "☆",
        titre: "Alliance Universelle",
        texte: "Le Rite entretient des traités d'amitié et de reconnaissance mutuelle avec des juridictions souveraines sur quatre continents."
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
        titre:  "Souverain Grand Commandeur",
        role:   "Fondateur du Rite",
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
        // À sa demande, pas de photographie : silhouette anonyme.
        img_data: RBI_AVATAR_ANONYME,
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
        titre:    "Brith Israël — L'Alliance de Lumière",
        sous:     "Tome I · Éditions COMPAS ŒIL — à paraître le 29 octobre 2026 · EAN 9782487319622",
        desc:     "Le fondement doctrinal et initiatique du Rite : un chemin enraciné dans la Genèse et la Kabbale, fondé sur des sources vérifiables. Au cœur du troisième degré, il place Joseph plutôt qu'Hiram — une trame attestée par le texte. Édition en librairie à paraître ; disponible dès à présent en édition CoolLibri.",
        placeholder: "L",
        liens: [
          { label: "CoolLibri", url: "https://www.coollibri.com/bibliotheque-en-ligne/mickael-darmon/brith-israel-lalliance-de-lumiere_1428718", style: "primary" },
          { label: "Précommander", url: "https://librairie-savoir-etre.com/produit/brith-israel/", style: "outline" }
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
      },
      {
        img_id:   "book-petrin",
        titre:    "Du Pétrin au Compas",
        sous:     "Roman — « Quand on cherche un secret, on trouve une vérité » · 9 juillet 2026",
        desc:     "Un roman. Laure Silvestri, journaliste d'investigation à Marseille, enquête sur les mardis soir de son compagnon boulanger. Ce n'est pas ce qu'elle croyait : c'est une Loge. Et ce qu'elle commence sans l'avoir prévu, c'est une initiation.",
        placeholder: "P",
        liens: [
          { label: "Amazon", url: "https://amzn.eu/d/05ZcIJ0g", style: "primary" }
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
    ligne1:  "Suprême Conseil du Rite Brith Israël",
    ligne2:  "© 2025 Rite Brith Israël — Tous droits réservés"
  }

};
