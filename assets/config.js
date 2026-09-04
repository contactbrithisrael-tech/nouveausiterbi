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
  // Le lien mène à la SECTION Joshua, et non directement au service.
  // Depuis qu'il est ouvert à tous, un curieux qui atterrit sans
  // préambule sur une fenêtre de conversation ne sait ni à qui il parle
  // ni ce qu'il peut demander. La section le lui dit, et porte le
  // bouton qui ouvre le service dans un onglet séparé — car c'est un
  // autre serveur, et on ne perd pas la page du Rite en cours de
  // lecture.
  { label: "Joshua — IA du RBI", href: "index.html#joshua" },
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
      },
      {
        icone: "◈",
        titre: "Joshua, l'IA du RBI",
        texte: "Une intelligence artificielle nourrie des seuls ouvrages du Rite, qui cite ouvrage et page pour chaque réponse et ne répond jamais de mémoire. Ouverte à tous — membres, visiteurs, curieux —, elle n'ouvre à chacun que les textes de son degré."
      }
    ]
  },

  /* ──────────────────────────────────────────────
     SECTION : JOSHUA — l'IA du Rite
     Publique, et placée avant le tuilage : Joshua est ouvert à tous,
     et l'annoncer après une porte réservée aux membres ferait croire
     l'inverse.
     ► Modifier ici la présentation de Joshua ◄
  ────────────────────────────────────────────── */
  joshua: {
    titre: "Joshua — l'IA du Rite Brith Israël",
    intro: "Ouvert à tous : aux membres de l'Ordre, aux Frères et Sœurs " +
           "d'autres rites, et aux curieux qui n'ont jamais mis les pieds " +
           "dans une Loge. Il ne demande qu'une chose au premier message : " +
           "à qui il parle.",
    cartes: [
      {
        icone: "◈",
        titre: "Ce qu'il est",
        texte: "Une intelligence artificielle nourrie des seuls ouvrages du " +
               "Rite — rituels, Bible du Rite, traités —, et de rien d'autre. " +
               "Ce n'est pas un moteur de recherche à qui l'on aurait appris " +
               "trois mots de kabbale."
      },
      {
        icone: "❝",
        titre: "Il cite, il n'invente pas",
        texte: "Chaque affirmation porte son ouvrage et sa page. Ce qu'il ne " +
               "trouve pas dans les textes, il le dit — au lieu de le " +
               "combler. C'est ce qui le distingue d'une IA générale, et " +
               "c'est la règle qui ne se négocie pas."
      },
      {
        icone: "📖",
        titre: "Il ouvre les sources",
        texte: "Le Rite cite la Torah, le Talmud, le Zohar — mais ne les " +
               "contient pas. La commande /source va chercher le passage " +
               "chez Sefaria et le rend tel quel : l'hébreu, le français, " +
               "et le lien. Vous vérifiez au lieu de le croire sur parole. " +
               "Avec /source+, la prononciation s'ajoute sous l'hébreu."
      },
      {
        icone: "▲",
        titre: "Il parle à votre degré",
        texte: "Un membre du degré N accède aux textes des degrés 1 à N, et " +
               "à aucun autre. Le filtre est appliqué par l'index avant même " +
               "que le texte soit lu : ce n'est pas une consigne de " +
               "politesse, c'est une arithmétique."
      },
      {
        icone: "🤝",
        titre: "Il reçoit les visiteurs",
        texte: "Frère ou Sœur d'un autre rite : un tuilage de vive voix, et " +
               "il compare son rite au vôtre, à la hauteur de votre grade. " +
               "Aucun rituel ne vous sera communiqué — vous en diriez autant " +
               "chez vous."
      },
      {
        icone: "✦",
        titre: "Il reçoit les profanes",
        texte: "Dites-lui simplement que vous n'êtes pas maçon. Il commence " +
               "alors par le commencement : ce qu'est la franc-maçonnerie, " +
               "d'où elle vient, ce qu'est ce Rite — sans jargon, et sans " +
               "mystères de pacotille."
      },
      {
        icone: "✓",
        titre: "Il vous fait travailler",
        texte: "Il propose de lui-même un questionnaire quand il sent le " +
               "degré compris, corrige chaque réponse avec sa source, et " +
               "délivre une attestation signée et scellée. En cas d'échec, " +
               "il dit quoi retravailler, où, et à quel grade."
      }
    ],
    /* Le mode d'emploi est SUR LE SITE et pas seulement dans /aide :
       une commande que personne ne connaît n'existe pas, et /aide ne se
       tape que par ceux qui savent déjà qu'il y a quelque chose à
       chercher. Des exemples réels, pas une liste de commandes — on
       apprend une syntaxe en la voyant employée. */
    modeEmploi: {
      titre: "Comment s'en servir",
      intro: "Il suffit d'écrire. Aucune commande n'est nécessaire pour " +
             "poser une question, se présenter ou demander à Joshua de " +
             "reprendre depuis le début. Les commandes ne servent qu'à " +
             "des choses précises — et une seule mérite d'être connue " +
             "de tous : celle qui ouvre les textes.",
      entrees: [
        {
          commande: "/source Genèse 1:1",
          titre: "Le texte juif, tel quel",
          texte: "Joshua va le chercher chez Sefaria et vous rend " +
                 "l'hébreu, le français et le lien. Vous vérifiez au " +
                 "lieu de le croire sur parole. Les livres se nomment " +
                 "comme vous en avez l'habitude : Genèse ou Bereshit, " +
                 "Psaumes ou Tehillim, Sanhédrin ou Sanhedrin, Pirke " +
                 "Avoth ou Pirkei Avot. Ces textes sont publics — nul " +
                 "besoin d'être connecté."
        },
        {
          commande: "/source+ Bereshit 1:1",
          titre: "Avec la prononciation",
          texte: "Le même passage, avec l'hébreu écrit en lettres " +
                 "latines sous le texte : « bereichit bara élohim èt " +
                 "hachamayim ve'èt ha'arets ». Pour dire le verset " +
                 "quand on ne déchiffre pas l'alphabet. C'est un peu " +
                 "plus long à venir, d'où le signe + : on ne l'impose " +
                 "pas à ceux qui lisent l'hébreu."
        },
        {
          commande: "/source RBI Tome II p. 45",
          titre: "Un ouvrage du Rite, à sa page",
          texte: "Réservé aux membres, et à leur degré seul. C'est la " +
                 "citation qui engage le plus : une erreur sur la Genèse " +
                 "se vérifie partout, une erreur sur le rituel d'un " +
                 "degré ne se vérifie nulle part ailleurs. Le mot RBI " +
                 "dit « l'ouvrage d'ici », quand un même titre peut " +
                 "désigner un traité et le livre qui le commente."
        },
        {
          commande: "/quiz    /quiz 3",
          titre: "Se faire interroger",
          texte: "Le questionnaire d'instruction de votre degré, ou " +
                 "celui d'un grade déjà reçu qu'on veut retravailler. " +
                 "Joshua corrige chaque réponse avec sa source et " +
                 "délivre une attestation en cas de réussite."
        },
        {
          commande: "/aide",
          titre: "Tout le reste",
          texte: "Inscription, connexion, tuilage des visiteurs, " +
                 "coordonnées au secrétariat, attestations, mot de " +
                 "passe. La liste complète, à tout moment."
        }
      ],
      note: "Sous chaque passage, Joshua rappelle sefarim.fr — la " +
            "traduction du Rabbinat. Une traduction reste un choix : " +
            "vous devez pouvoir aller voir ailleurs sans le demander."
    },

    pourquoi: {
      titre: "Pourquoi une intelligence artificielle ?",
      paragraphes: [
        "Parce qu'un Frère qui travaille son degré à minuit n'a personne à " +
        "qui demander. L'instruction se donne en Loge, une fois par mois ; " +
        "l'étude, elle, se fait tous les jours, et c'est là qu'on abandonne.",

        "Parce qu'une IA générale répond à tout, avec aplomb, et se trompe " +
        "sur ce Rite-ci — dont les textes ne sont nulle part sur internet. " +
        "Elle plaquerait le Rite Écossais sur nos degrés et personne ne s'en " +
        "apercevrait. Joshua ne connaît que nos ouvrages, et refuse de " +
        "répondre quand ils se taisent.",

        "Parce que le degré, justement, se garde mieux par une machine que " +
        "par une bonne volonté : un index qui filtre ne se laisse pas " +
        "attendrir, ne se trompe pas de Frère et n'oublie pas la règle un " +
        "soir de fatigue.",

        "Et parce qu'elle dit ce qu'elle est. Joshua se présente comme une " +
        "machine dès la première phrase, ne joue jamais au Frère en chair " +
        "et en os, et ne remplace ni l'instruction en Loge, ni le Vénérable " +
        "Maître. Il fait une chose : il tient les textes ouverts entre deux " +
        "tenues."
      ]
    },
    bouton: "Parler à Joshua",
    lien: "https://joshua-studio.onrender.com/joshua",
    note: "Aucun contenu de rituel n'est communiqué à qui n'en a pas reçu les degrés."
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
    /* Annonce faite AVANT le tuilage du site, et redite après : un Frère
       d'un autre rite n'a pas besoin des documents réservés, il vient
       pour comprendre. Lui faire passer un tuilage pour découvrir qu'il
       y avait une autre porte serait le perdre en route.

       Elle nomme aussi le profane, depuis que Joshua le reçoit. Celui
       qui tombe sur un tuilage sans y être nommé se croit à la mauvaise
       adresse, et personne ne le détrompe. */
    visiteur: {
      titre: "Vous n'êtes pas membre du Rite ?",
      texte: "Vous n'avez pas besoin de ce tuilage pour venir vous renseigner. " +
             "Joshua, l'assistant d'étude du Rite, reçoit les Frères et Sœurs " +
             "d'autres rites après un simple tuilage de vive voix, et répond à " +
             "leurs questions : l'origine du Rite, sa structure, ce qui le " +
             "distingue du leur. " +
             "Et si vous n'êtes pas franc-maçon du tout, dites-le-lui : il " +
             "vous est ouvert aussi, et il commence alors par le commencement " +
             "— ce qu'est la franc-maçonnerie, et ce qu'est ce Rite. " +
             "Écrivez-lui bonjour, il fait le reste.",
      bouton: "Poser une question à Joshua",
      lien: "https://joshua-studio.onrender.com/joshua",
      note: "Aucun contenu de rituel n'est communiqué à qui n'en a pas reçu les degrés."
    },
    max_essais: 3,           // Nombre d'essais par question
    questions: [
      {
        id:       "q1",
        texte:    "D'où venez-vous ?",
        // Reconnu à ce que la réponse contient : « de Saint-Jean », « de la
        // loge de St Jean », « d'une Loge Saint Jean »… La liste ci-dessous
        // reste le repli si « motif » est retiré.
        motif:    "(saint|st) ?jean",
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
        motif:    "(^| )(3|5|7|trois|cinq|sept)( |$)",
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
