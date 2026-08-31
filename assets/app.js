/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — app.js

   Lit RBI_CONFIG (config.js) et construit toute la page.
   Ne jamais modifier ce fichier pour changer du contenu :
   tout est dans config.js.

   ── ARCHITECTURE (décisions et raisons) ──────────────────────

   1) Trois couches, trois fichiers, une seule direction de
      dépendance :
          config.js  (DONNÉES)   → aucune dépendance
          app.js     (STRUCTURE) → lit config.js
          images.js  (MÉDIAS)    → lit le DOM produit par app.js
      Le contenu éditorial est ainsi modifiable par une personne
      non développeuse sans jamais ouvrir de code de rendu, et
      une erreur de saisie dans config.js ne peut pas casser la
      logique de la page.

   2) Aucun framework, aucune étape de build, ES5 volontaire.
      Le site est publié en statique (dépôt → hébergement de
      fichiers). Introduire un bundler imposerait une chaîne
      d'outils et une étape de compilation à chaque correction de
      texte, ce qui annulerait le bénéfice du point 1). Le coût
      accepté en échange : pas de modules, d'où l'IIFE ci-dessous.

   3) IIFE + 'use strict' : le fichier n'expose STRICTEMENT rien
      au scope global. Les pages annexes (roue.html, traites.html,
      espace-membres.html) embarquent leurs propres scripts inline ;
      isoler app.js garantit qu'aucune collision de nom ne peut
      survenir entre eux.

   4) Le HTML (index.html) ne contient que des conteneurs vides
      identifiés par `id`. Ces `id` forment le contrat entre les
      trois couches : app.js les remplit, images.js les retrouve.
      Un conteneur absent n'est jamais une erreur fatale — d'où
      les gardes `if (el)` systématiques : la même version d'app.js
      dessert plusieurs pages qui n'ont pas toutes les sections.
════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // Capture de la config au chargement du script, donc AVANT
  // DOMContentLoaded. Si config.js manquait, `C` vaudrait undefined
  // sans lever d'erreur ici : la seule vérification utile est donc
  // faite dans INIT, au moment où l'on va réellement s'en servir.
  var C = window.RBI_CONFIG;

  /* ── Utilitaires ────────────────────────────── */
  function $(id) { return document.getElementById(id); }

  /* Micro-fabrique de nœuds DOM — remplace un moteur de templates.
     Choix structurant : la clé `text` (textContent) est la voie
     normale, la clé `html` (innerHTML) est une exception explicite.
     Tout ce qui vient de config.js passe donc par textContent et se
     retrouve échappé par le navigateur : une apostrophe, un « & » ou
     un chevron saisi par l'éditeur du site ne peut ni casser le
     balisage ni injecter de script. `html` n'est utilisé que sur des
     gabarits écrits ici, jamais sur une valeur de config brute. */
  function el(tag, props, children) {
    var e = document.createElement(tag);
    if (props) {
      Object.keys(props).forEach(function (k) {
        if (k === 'class')      e.className = props[k];
        else if (k === 'html')  e.innerHTML = props[k];
        else if (k === 'text')  e.textContent = props[k];
        else                    e.setAttribute(k, props[k]);
      });
    }
    if (children) {
      children.forEach(function (c) { if (c) e.appendChild(c); });
    }
    return e;
  }

  /* Normalisation de saisie utilisée par le tuilage.
     NFD décompose « é » en « e » + accent combinant, que la plage
     U+0300-U+036F supprime ensuite : on compare donc sans accents,
     sans casse, sans ponctuation et sans espaces multiples.
     Elle est appliquée AUX DEUX CÔTÉS de la comparaison (saisie ET
     réponses de config.js) pour que l'éditeur du site puisse écrire
     ses réponses en français naturel, accents compris, sans avoir à
     connaître cette normalisation. */
  function normalise(str) {
    return (str || '')
      .toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /* ════════════════════════════════════════════════
     1. NAVBAR
  ════════════════════════════════════════════════ */
  function buildNavbar() {
    var cfg = C.navbar;

    var brand = $('navbar-brand');
    if (brand) {
      brand.innerHTML = '';
      var logo = el('img', { id: 'nav-logo', src: '', alt: cfg.nom, class: 'navbar__logo' });
      var title = el('div', { class: 'navbar__title' }, [
        el('span', { class: 'navbar__name', text: cfg.nom }),
        el('span', { class: 'navbar__hebrew', text: cfg.hebrew })
      ]);
      brand.appendChild(logo);
      brand.appendChild(title);
    }

    var ul = $('nav-links');
    if (ul && cfg.liens) {
      ul.innerHTML = '';
      cfg.liens.forEach(function (lien) {
        var cls = 'nav-link';
        if (lien.style === 'discret') cls += ' nav-link--tuilage';
        if (lien.style === 'cta')     cls += ' nav-link--cta';
        var attributs = { href: lien.href, class: cls, text: lien.label };
        // Un lien vers un autre service s'ouvre dans un onglet séparé, et
        // « noopener » l'empêche de reprendre la main sur la page qui
        // l'a ouvert — une page tierce peut sinon rediriger l'onglet
        // d'origine à l'insu du lecteur.
        if (lien.cible) {
          attributs.target = lien.cible;
          attributs.rel = 'noopener';
        }
        ul.appendChild(el('li', {}, [el('a', attributs)]));
      });
    }
  }

  /* ════════════════════════════════════════════════
     2. HERO
  ════════════════════════════════════════════════ */
  function buildHero() {
    var cfg = C.hero;

    var b = $('hero-banner');
    if (b) b.innerHTML = '<span class="banner__text">' + cfg.bandeau + '</span>';

    var t = $('hero-title');
    if (t) t.innerHTML =
      '<span class="hero__title-fr">' + cfg.titre_fr + '</span>' +
      '<span class="hero__title-he" dir="rtl">' + cfg.titre_he + '</span>';

    var s = $('hero-subtitle');
    if (s) s.innerHTML = cfg.subtitle + '<br><em>' + cfg.subtitle2 + '</em>';

    var cta = $('hero-cta');
    if (cta) cta.innerHTML =
      '<a href="#rite" class="btn btn--primary">' + cfg.btn_decouvrir + '</a>' +
      '<a href="devenir-fm.html" class="btn btn--outline">' + cfg.btn_rejoindre + '</a>';
  }

  /* ════════════════════════════════════════════════
     3. SECTION RITE
  ════════════════════════════════════════════════ */
  function buildRite() {
    var cfg = C.rite;
    var t = $('rite-titre'); if (t) t.textContent = cfg.titre;
    var i = $('rite-intro'); if (i) i.textContent = cfg.intro;

    var grid = $('rite-cards');
    if (grid && cfg.cartes) {
      grid.innerHTML = '';
      cfg.cartes.forEach(function (c) {
        grid.appendChild(el('div', { class: 'card reveal' }, [
          el('span', { class: 'card__icon', text: c.icone }),
          el('h3',   { class: 'card__title', text: c.titre }),
          el('p',    { class: 'card__text',  text: c.texte })
        ]));
      });
      // Le bouton « Roue des 33 Degrés » est inséré comme FRÈRE de
      // la grille, pas comme enfant : placé dedans, il deviendrait une
      // cellule de la grille CSS et s'alignerait comme une carte.
      var roueWrap = document.createElement('div');
      roueWrap.className = 'rite-roue-wrap reveal';
      roueWrap.innerHTML = '<a href="roue.html" class="btn btn--outline">✡ Découvrir la Roue des 33 Degrés</a>';
      grid.parentNode.insertBefore(roueWrap, grid.nextSibling);
    }
  }

  /* ════════════════════════════════════════════════
     4. CHEFS DE L'ORDRE
  ════════════════════════════════════════════════ */
  function buildChefs() {
    var cfg = C.chefs;
    var t = $('chefs-titre'); if (t) t.textContent = cfg.titre;

    var grid = $('chefs-grid');
    if (!grid || !cfg.membres) return;
    grid.innerHTML = '';

    cfg.membres.forEach(function (m) {
      // `src` volontairement vide : la photo (base64) est posée plus
      // tard par images.js, qui retrouve la balise par `m.img_id`.
      // Le placeholder (initiale du nom) est empilé DESSOUS par le CSS
      // et reste visible tant qu'aucune source n'a été injectée : la
      // mise en page ne bouge donc pas si une photo manque.
      var photoDiv = el('div', { class: 'chef-card__photo-wrap' }, [
        el('img', { src: '', id: m.img_id, alt: m.nom, class: 'chef-card__photo' }),
        el('div', { class: 'chef-card__photo-placeholder', text: m.nom.charAt(0) })
      ]);

      var badge = el('span', {
        class: 'chef-card__grade chef-card__grade--' + m.rang,
        text:  m.grade
      });

      var card = el('div', { class: 'chef-card chef-card--' + m.rang + ' reveal' }, [
        photoDiv,
        badge,
        el('h3', { class: 'chef-card__nom',   text: m.nom   }),
        el('p',  { class: 'chef-card__titre',  text: m.titre }),
        el('p',  { class: 'chef-card__role',   text: m.role  })
      ]);
      // Le listener est posé sur la carte entière (et non sur la seule
      // photo) et capture `m` par fermeture : la lightbox reçoit ainsi
      // l'objet de configuration d'origine, sans avoir à relire le DOM
      // pour reconstituer nom, titre et rôle.
      card.style.cursor = 'pointer';
      card.addEventListener('click', function() { ouvrirLightboxChef(m); });
      grid.appendChild(card);
    });
  }

  /* ════════════════════════════════════════════════
     5. LIVRES
  ════════════════════════════════════════════════ */
  function buildLivres() {
    var cfg = C.livres;
    var t = $('livres-titre'); if (t) t.textContent = cfg.titre;

    var grid = $('books-grid');
    if (!grid || !cfg.liste) return;
    grid.innerHTML = '';

    cfg.liste.forEach(function (book) {
      var btns = book.liens.map(function (lien) {
        return el('a', {
          href: lien.url,
          target: '_blank',
          rel: 'noopener',
          class: 'btn btn--sm btn--' + (lien.style || 'primary'),
          text: lien.label
        });
      });
      var linksDiv = el('div', { class: 'book-card__links' }, btns);

      var coverWrap = el('div', { class: 'book-card__cover' }, [
        el('img', { src: '', id: book.img_id, alt: book.titre, class: 'book-card__img', style: 'cursor:pointer' }),
        el('div', { class: 'book-card__cover-placeholder', text: book.placeholder })
      ]);
      coverWrap.style.cursor = 'pointer';
      coverWrap.addEventListener('click', function() { ouvrirLightboxLivre(book); });

      var infoDiv = el('div', { class: 'book-card__info' }, [
        el('h3', { class: 'book-card__title', text: book.titre }),
        el('p',  { class: 'book-card__subtitle', text: book.sous }),
        el('p',  { class: 'book-card__desc', text: book.desc }),
        linksDiv
      ]);

      grid.appendChild(el('div', { class: 'book-card reveal' }, [coverWrap, infoDiv]));
    });
  }

  /* ════════════════════════════════════════════════
     6. TUILAGE

     ⚠ PORTÉE DU DISPOSITIF — à lire avant toute évolution.
     Le tuilage est un filtre d'usage, PAS un contrôle d'accès.
     Questions, réponses acceptées et documents déverrouillés sont
     tous livrés au navigateur (config.js et images.js sont publics
     et lisibles) : quiconque ouvre les outils de développement les
     obtient sans répondre. C'est un compromis assumé, imposé par
     l'hébergement statique — il n'existe aucun serveur pour tenir
     un secret. Toute pièce réellement confidentielle doit être
     servie par un back-end authentifié, jamais ajoutée ici.

     Machine à états : toutes les étapes (démarrage, une étape par
     question, succès, échec) sont construites d'un coup puis
     masquées par classe CSS. On ne reconstruit jamais le DOM en
     cours de parcours — les `id` restent donc stables et les
     écouteurs, posés une seule fois, survivent à tout le parcours,
     y compris après un « Recommencer ».
  ════════════════════════════════════════════════ */
  function buildTuilage() {
    var cfg = C.tuilage;
    var t = $('tuilage-titre'); if (t) t.textContent = cfg.titre;
    var i = $('tuilage-intro'); if (i) i.textContent = cfg.intro;

    var zone = $('tuilage-zone');
    if (!zone) return;

    zone.innerHTML = '';

    var stepStart = el('div', { class: 'tuilage__step', id: 'tuilage-start' }, [
      el('button', { class: 'btn btn--primary btn--lg', id: 'tuilage-start-btn', text: 'Commencer le Tuilage' })
    ]);

    var stepEls = cfg.questions.map(function (q, idx) {
      var n = idx + 1;
      return el('div', { class: 'tuilage__step tuilage__step--hidden', id: 'tuilage-' + q.id }, [
        el('p',      { class: 'tuilage__question', text: q.texte }),
        el('div',    { class: 'tuilage__input-group' }, [
          el('input',  { type: 'text', id: 'tuilage-input-' + n, class: 'tuilage__input', placeholder: 'Votre réponse…', autocomplete: 'off' }),
          el('button', { class: 'btn btn--primary', id: 'tuilage-btn-' + n, text: 'Répondre' })
        ]),
        el('p', { class: 'tuilage__feedback', id: 'tuilage-feedback-' + n })
      ]);
    });

    var pdfBtns = cfg.pdfs.map(function (p) {
      return el('a', { href: '#', class: 'btn btn--outline', id: p.id, style: 'display:none', text: '📄 ' + p.label });
    });
    var stepSucces = el('div', { class: 'tuilage__step tuilage__step--hidden', id: 'tuilage-success' }, [
      el('div', { class: 'tuilage__success' }, [
        el('span', { class: 'tuilage__success-icon', text: cfg.succes.icone }),
        el('h3',   { text: cfg.succes.titre }),
        el('p',    { text: cfg.succes.message }),
        el('div',  { class: 'tuilage__docs', id: 'tuilage-docs' }, pdfBtns),
        el('a', { class: 'btn btn--primary', href: 'espace-membres.html', text: '✡ Accéder à l\'Espace Membres' })
      ])
    ]);

    var stepEchec = el('div', { class: 'tuilage__step tuilage__step--hidden', id: 'tuilage-fail' }, [
      el('div', { class: 'tuilage__fail' }, [
        el('span', { class: 'tuilage__fail-icon', text: '✕' }),
        el('p',    { text: cfg.echec.message }),
        el('button', { class: 'btn btn--outline', id: 'tuilage-retry-btn', text: 'Recommencer' })
      ])
    ]);

    zone.appendChild(stepStart);
    stepEls.forEach(function (s) { zone.appendChild(s); });
    zone.appendChild(stepSucces);
    zone.appendChild(stepEchec);

    /* État du parcours, confiné à cette fonction (aucune variable
       globale) : un compteur d'essais PAR question — et non un
       compteur unique — pour qu'une erreur sur la première question
       ne consomme pas le crédit de la seconde. */
    var essais = cfg.questions.map(function () { return 0; });
    var qIdx   = 0;
    var MAX    = cfg.max_essais || 3;

    /* Un seul chemin pour changer d'étape : on masque tout, puis on
       révèle la cible. Cela rend impossible l'état incohérent « deux
       étapes visibles » quel que soit l'enchaînement des clics. */
    function showStep(id) {
      zone.querySelectorAll('.tuilage__step').forEach(function (s) {
        s.classList.add('tuilage__step--hidden');
      });
      var target = $(id);
      if (target) {
        target.classList.remove('tuilage__step--hidden');
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    function setFb(n, msg, type) {
      var fb = $('tuilage-feedback-' + n);
      if (fb) {
        fb.textContent = msg;
        fb.className   = 'tuilage__feedback tuilage__feedback--' + type;
      }
    }

    function verif(idx) {
      var n   = idx + 1;
      var q   = cfg.questions[idx];
      var inp = $('tuilage-input-' + n);
      if (!inp) return;
      var val = normalise(inp.value);

      var ok = q.reponses.some(function (r) { return normalise(r) === val; });

      if (ok) {
        setFb(n, 'Bien répondu, Frère.', 'ok');
        if (idx + 1 < cfg.questions.length) {
          // Délai de 900 ms : le message de confirmation doit rester
          // lisible avant que l'étape suivante ne le remplace. C'est
          // un temps de lecture, pas une temporisation technique.
          setTimeout(function () {
            qIdx = idx + 1;
            showStep('tuilage-' + cfg.questions[qIdx].id);
            var nextInp = $('tuilage-input-' + (qIdx + 1));
            if (nextInp) nextInp.focus();
          }, 900);
        } else {
          setTimeout(function () { showStep('tuilage-success'); }, 900);
        }
      } else {
        essais[idx]++;
        if (essais[idx] >= MAX) {
          showStep('tuilage-fail');
        } else {
          setFb(n, 'Je ne vous reconnais pas. Essai ' + essais[idx] + '/' + MAX + '.', 'error');
          inp.value = '';
          inp.focus();
        }
      }
    }

    function resetTuilage() {
      essais = cfg.questions.map(function () { return 0; });
      qIdx   = 0;
      cfg.questions.forEach(function (q, idx) {
        var n = idx + 1;
        var inp = $('tuilage-input-' + n);
        var fb  = $('tuilage-feedback-' + n);
        if (inp) inp.value   = '';
        if (fb)  fb.textContent = '';
      });
      showStep('tuilage-start');
    }

    var startBtn = $('tuilage-start-btn');
    if (startBtn) {
      startBtn.addEventListener('click', function () {
        showStep('tuilage-' + cfg.questions[0].id);
        setTimeout(function () {
          var f = $('tuilage-input-1');
          if (f) f.focus();
        }, 400);
      });
    }

    // Liaison unique des écouteurs : `idx` est capturé par la
    // fermeture de callback, ce qui évite de le relire dans le DOM et
    // garantit que chaque bouton reste lié à sa question même si la
    // liste de config.js est réordonnée.
    cfg.questions.forEach(function (q, idx) {
      var n   = idx + 1;
      var btn = $('tuilage-btn-' + n);
      var inp = $('tuilage-input-' + n);
      if (btn) btn.addEventListener('click', function () { verif(idx); });
      if (inp) inp.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') verif(idx);
      });
    });

    var retryBtn = $('tuilage-retry-btn');
    if (retryBtn) retryBtn.addEventListener('click', resetTuilage);
  }

  /* ════════════════════════════════════════════════
     7. CONTACT
  ════════════════════════════════════════════════ */
  function buildContact() {
    var cfg = C.contact;
    var t = $('contact-titre'); if (t) t.textContent = cfg.titre;
    var i = $('contact-intro'); if (i) i.textContent = cfg.intro;

    var block = $('contact-block');
    if (!block) return;
    block.innerHTML = '';

    block.appendChild(el('a', {
      href:  'mailto:' + cfg.email,
      class: 'contact-block__email',
      text:  cfg.email
    }));
    block.appendChild(el('a', {
      href: cfg.facebook.url, target: '_blank', rel: 'noopener',
      class: 'btn btn--outline', text: cfg.facebook.label
    }));
    block.appendChild(el('a', {
      href: cfg.traites.url, class: 'btn btn--primary', text: cfg.traites.label
    }));
    block.appendChild(el('a', {
      href: 'https://forms.gle/G6mB3CpbLfmGzE219',
      target: '_blank', rel: 'noopener',
      class: 'btn btn--primary',
      text: '✡ Devenir Franc-Maçon'
    }));
  }

  /* ════════════════════════════════════════════════
     8. FOOTER
  ════════════════════════════════════════════════ */
  function buildFooter() {
    var cfg = C.footer;
    var fc = $('footer-content');
    if (!fc) return;
    fc.innerHTML = '';
    fc.appendChild(el('p', { class: 'footer__logo-text', text: cfg.hebrew }));
    fc.appendChild(el('p', { class: 'footer__line', text: cfg.ligne1 }));
    fc.appendChild(el('p', { class: 'footer__line footer__line--sm', text: cfg.ligne2 }));
  }

  /* ════════════════════════════════════════════════
     9. BURGER MENU
  ════════════════════════════════════════════════ */
  function initBurger() {
    var btn     = $('burger-btn');
    var menu    = $('nav-menu');
    var overlay = $('nav-overlay');
    if (!btn || !menu) return;

    function open() {
      btn.classList.add('is-open');
      menu.classList.add('is-open');
      if (overlay) overlay.classList.add('is-visible');
      btn.setAttribute('aria-expanded', 'true');
      menu.setAttribute('aria-hidden',  'false');
      document.body.style.overflow = 'hidden';
    }
    function close() {
      btn.classList.remove('is-open');
      menu.classList.remove('is-open');
      if (overlay) overlay.classList.remove('is-visible');
      btn.setAttribute('aria-expanded', 'false');
      menu.setAttribute('aria-hidden',  'true');
      document.body.style.overflow = '';
    }

    btn.addEventListener('click', function () {
      btn.classList.contains('is-open') ? close() : open();
    });
    if (overlay) overlay.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    menu.addEventListener('click', function (e) {
      if (e.target.classList.contains('nav-link')) close();
    });
  }

  /* ════════════════════════════════════════════════
     10. ÉTOILES HERO
  ════════════════════════════════════════════════ */
  function initStars() {
    var container = $('stars-container');
    if (!container) return;
    // DocumentFragment : les 120 étoiles sont assemblées hors document
    // et insérées en une seule fois — un seul recalcul de mise en page
    // au lieu de 120.
    var frag = document.createDocumentFragment();
    for (var i = 0; i < 120; i++) {
      var s = document.createElement('div');
      s.className = 'star';
      // Le hasard ne sert qu'à SEMER des variables CSS ; l'animation
      // elle-même est décrite dans style.css et exécutée par le
      // compositeur du navigateur. Aucune boucle JS n'anime le ciel :
      // le scintillement ne coûte rien au fil d'exécution principal.
      var size = Math.random() * 2 + 0.5;
      s.style.cssText =
        'left:'    + (Math.random() * 100) + '%;' +
        'top:'     + (Math.random() * 100) + '%;' +
        'width:'   + size + 'px;height:' + size + 'px;' +
        '--op-min:'+ (Math.random() * 0.15 + 0.05) + ';' +
        '--op-max:'+ (Math.random() * 0.6  + 0.3 ) + ';' +
        '--dur:'   + (Math.random() * 4    + 2   ) + 's;' +
        '--delay:' + (Math.random() * 5         ) + 's;';
      frag.appendChild(s);
    }
    container.appendChild(frag);
  }

  /* ════════════════════════════════════════════════
     11. NAVBAR SCROLL
  ════════════════════════════════════════════════ */
  function initNavbarScroll() {
    var navbar = $('navbar');
    if (!navbar) return;
    // `passive: true` : promesse faite au navigateur que ce handler
    // n'appellera pas preventDefault(), ce qui lui permet de continuer
    // le défilement sans attendre l'exécution du callback.
    // On bascule une classe plutôt qu'un style inline : l'apparence et
    // la transition restent entièrement décrites dans style.css.
    window.addEventListener('scroll', function () {
      navbar.classList.toggle('scrolled', window.scrollY > 40);
    }, { passive: true });
  }

  /* ════════════════════════════════════════════════
     12. SCROLL REVEAL
  ════════════════════════════════════════════════ */
  function initReveal() {
    // Dégradation gracieuse : sans IntersectionObserver (navigateurs
    // anciens), tout est révélé immédiatement. Le contenu prime sur
    // l'animation — jamais de texte rendu invisible par une API
    // manquante.
    var els = document.querySelectorAll('.reveal');
    if (!('IntersectionObserver' in window)) {
      els.forEach(function (e) { e.classList.add('is-visible'); });
      return;
    }
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          // Animation à usage unique : on cesse d'observer l'élément
          // révélé. L'observateur se vide au fil du défilement au lieu
          // de rappeler indéfiniment à chaque aller-retour.
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    els.forEach(function (e) { obs.observe(e); });
  }

  /* ════════════════════════════════════════════════
     LIGHTBOX LIVRES

     Créée à la demande et détruite à la fermeture, plutôt que
     préconstruite et masquée : les visuels sont des data-URI base64
     de plusieurs centaines de kilo-octets, les garder en double dans
     le document coûterait cette mémoire en permanence, pour une vue
     que la plupart des visiteurs n'ouvriront jamais.
  ════════════════════════════════════════════════ */
  function ouvrirLightboxLivre(book) {
    // Purge d'une éventuelle instance précédente : garantit l'unicité
    // de l'id et évite l'empilement de lightbox sur double clic.
    var existing = document.getElementById('book-lightbox');
    if (existing) existing.remove();

    // On relit le `src` DÉJÀ injecté dans la page par images.js au lieu
    // de repartir de la source base64 : le navigateur réutilise l'image
    // déjà décodée, l'ouverture est instantanée et sans second décodage.
    var imgEl = document.getElementById(book.img_id);
    var front = imgEl ? imgEl.src : '';
    var back  = imgEl ? (imgEl.dataset.back || '') : '';

    var lb = document.createElement('div');
    lb.id = 'book-lightbox';
    lb.innerHTML =
      '<div class="lb-overlay"></div>' +
      '<div class="lb-book-box">' +
        '<button class="lb-close">✕</button>' +
        '<h3 class="lb-book-titre">' + book.titre + '</h3>' +
        '<div class="lb-book-pages">' +
          (front ? '<img src="' + front + '" class="lb-book-img" alt="Couverture">' : '') +
          (back  ? '<img src="' + back  + '" class="lb-book-img" alt="4e de couverture">' : '') +
        '</div>' +
        '<div class="lb-book-links">' +
          book.liens.map(function(l) {
            return '<a href="' + l.url + '" target="_blank" rel="noopener" class="btn btn--primary btn--sm">' + l.label + '</a>';
          }).join('') +
        '</div>' +
      '</div>';

    document.body.appendChild(lb);
    lb.querySelector('.lb-overlay').addEventListener('click', function() { lb.remove(); });
    lb.querySelector('.lb-close').addEventListener('click',   function() { lb.remove(); });
    // Handler nommé pour pouvoir se retirer lui-même : la lightbox
    // étant recréée à chaque ouverture, un écouteur anonyme laissé sur
    // `document` s'accumulerait à chaque consultation (fuite mémoire
    // et fermetures fantômes).
    document.addEventListener('keydown', function esc(e) {
      if (e.key === 'Escape') { lb.remove(); document.removeEventListener('keydown', esc); }
    });
  }

  /* ════════════════════════════════════════════════
     13. LIGHTBOX CHEFS
  ════════════════════════════════════════════════ */
  function ouvrirLightboxChef(m) {
    var existing = document.getElementById('chef-lightbox');
    if (existing) existing.remove();

    var img = document.getElementById(m.img_id);
    var src = img ? img.src : '';

    var lb = document.createElement('div');
    lb.id = 'chef-lightbox';
    lb.innerHTML =
      '<div class="lb-overlay"></div>' +
      '<div class="lb-box">' +
        '<button class="lb-close">✕</button>' +
        (src ? '<img src="' + src + '" class="lb-img" alt="' + m.nom + '">' : '<div class="lb-placeholder">' + m.nom.charAt(0) + '</div>') +
        '<div class="lb-info">' +
          '<h2 class="lb-nom">' + m.nom + '</h2>' +
          '<p class="lb-titre">' + m.titre + '</p>' +
          '<p class="lb-role">' + m.role + '</p>' +
        '</div>' +
      '</div>';

    document.body.appendChild(lb);
    lb.querySelector('.lb-overlay').addEventListener('click', function() { lb.remove(); });
    lb.querySelector('.lb-close').addEventListener('click', function() { lb.remove(); });
    // Handler nommé pour pouvoir se retirer lui-même : la lightbox
    // étant recréée à chaque ouverture, un écouteur anonyme laissé sur
    // `document` s'accumulerait à chaque consultation (fuite mémoire
    // et fermetures fantômes).
    document.addEventListener('keydown', function esc(e) {
      if (e.key === 'Escape') { lb.remove(); document.removeEventListener('keydown', esc); }
    });
  }

  /* ════════════════════════════════════════════════
     INIT

     Ordre imposé, en deux temps :
       1. les build*() écrivent le DOM à partir de la config ;
       2. les init*() branchent les comportements sur ce DOM.
     L'inverse échouerait silencieusement : initReveal() n'observerait
     aucune carte et initBurger() ne trouverait pas de lien à fermer,
     puisque ces nœuds n'existent pas encore.

     images.js, chargé après app.js, s'abonne au même DOMContentLoaded
     et s'exécutera donc APRÈS ce bloc (les écouteurs d'un même
     événement sont appelés dans leur ordre d'enregistrement) : les
     balises qu'il doit remplir sont garanties présentes.
  ════════════════════════════════════════════════ */
  document.addEventListener('DOMContentLoaded', function () {
    // Échec explicite et unique point de contrôle de la dépendance :
    // sans config.js il n'y a rien à construire, et poursuivre ne
    // produirait qu'une cascade de TypeError illisibles.
    if (!window.RBI_CONFIG) {
      console.error('[RBI] config.js introuvable !');
      return;
    }
    /* 1. Construire le contenu */
    buildNavbar();
    buildHero();
    buildRite();
    buildChefs();
    buildLivres();
    buildTuilage();
    buildContact();
    buildFooter();

    /* 2. Activer les comportements */
    initBurger();
    initStars();
    initNavbarScroll();
    initReveal();
  });

})();
