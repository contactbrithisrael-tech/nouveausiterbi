/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — musique du Rite

   Le son est celui d'une vidéo YouTube choisie pour le site. La
   vidéo n'est jamais affichée : seul son son est diffusé, par un
   lecteur réduit à un point invisible.

   ── Pourquoi passer par YouTube ────────────────────────────────
   Diffuser un morceau qu'on ne possède pas suppose que l'ayant
   droit soit rémunéré. L'intégration YouTube le fait : l'écoute est
   comptée pour lui. Extraire la bande son pour l'héberger ici ne le
   ferait pas — et serait une contrefaçon.

   ── Le démarrage : ce qu'aucun site ne peut contourner ─────────
   Aucun navigateur n'autorise un site à produire du son avant que
   le visiteur n'ait touché la page. La règle est absolue et vaut
   pour tous les sites du monde, YouTube compris. Un site qui
   semble démarrer seul fait en réalité ce que fait celui-ci :

     1. la musique part dès l'ouverture, mais en sourdine — ce que
        les navigateurs autorisent ;
     2. au tout premier geste du visiteur, quel qu'il soit — un
        clic, une touche, un défilement, un doigt sur l'écran — le
        son monte en fondu.

   Le visiteur n'a donc rien à chercher ni à cliquer : la musique
   arrive d'elle-même dès qu'il commence à lire.

   ── D'une page à l'autre ───────────────────────────────────────
   Le choix du visiteur et l'endroit du morceau sont retenus le
   temps de la visite. Qui demande le silence ne le redemande pas à
   chaque page ; qui écoute reprend là où il en était plutôt qu'au
   début.

   ── Réglages ───────────────────────────────────────────────────
   Tout se modifie dans REGLAGES ci-dessous. Pour changer de
   morceau, remplacer VIDEO par l'identifiant de la nouvelle vidéo —
   les onze caractères qui suivent « youtu.be/ » ou « ?v= ».

   ── Usage ──────────────────────────────────────────────────────
   Inclure <script src="assets/musique.js?v=20260901c"></script>
   avant la fermeture du <body>. Le numéro de version n'est pas
   décoratif : _headers conserve les fichiers d'assets un an, et
   c'est le changement d'adresse qui force les navigateurs à
   reprendre la nouvelle version. Modifier ce fichier sans changer
   le numéro revient à ne rien publier du tout.
════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // Les onze caractères qui identifient la vidéo.
  var VIDEO = '_pGXBoOsrJI';

  var REGLAGES = {
    volume:       18,      // volume final, de 0 à 100 — volontairement discret
    fondu:        3000,    // durée du fondu d'ouverture et de fermeture, en ms
    positionCoin: 'right'  // 'right' ou 'left'
  };

  // Mémoire du visiteur.
  //
  // Le refus du son est retenu durablement : quelqu'un qui a coupé la
  // musique ne doit pas la retrouver au visage à sa prochaine visite.
  // L'endroit du morceau, lui, n'a de sens que le temps d'une visite.
  var CLE_CHOIX = 'rbi-musique';    // durable
  var CLE_TEMPS = 'rbi-musique-t';  // le temps de la visite

  var lecteur = null;
  var joue = false;
  var sourdine = true;       // vrai tant qu'aucun geste n'a eu lieu
  var fonduEnCours = null;
  var apiDemandee = false;
  var majInterface = null;   // fixée par construireLecteur()
  var boiteLecteur = null;   // le cadre visible, idem

  /* ── Mémoire, tolérante aux navigations privées verrouillées ────
     Certains navigateurs refusent tout accès au stockage : chaque
     lecture et chaque écriture doit pouvoir échouer sans conséquence.
     Le site fonctionne alors normalement, simplement sans mémoire. */
  function coffre(cle) {
    return cle === CLE_CHOIX ? window.localStorage : window.sessionStorage;
  }
  function lire(cle, defaut) {
    try { var v = coffre(cle).getItem(cle); return v === null ? defaut : v; }
    catch (e) { return defaut; }
  }
  function ecrire(cle, valeur) {
    try { coffre(cle).setItem(cle, valeur); } catch (e) { /* sans importance */ }
  }

  /* ── Chargement de l'API, une seule fois ───────────────────────── */
  function chargerAPI(quandPrete, siEchec) {
    if (window.YT && window.YT.Player) { quandPrete(); return; }

    if (!apiDemandee) {
      apiDemandee = true;
      var s = document.createElement('script');
      s.src = 'https://www.youtube.com/iframe_api';
      s.onerror = siEchec;
      document.head.appendChild(s);
    }

    var precedent = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function () {
      if (typeof precedent === 'function') precedent();
      quandPrete();
    };

    // Réseau coupé, extension qui bloque, API muette : sans garde-fou
    // le bouton resterait figé sur « Chargement… ».
    setTimeout(function () {
      if (!window.YT || !window.YT.Player) siEchec();
    }, 8000);
  }

  /* ── Le lecteur : un point invisible, jamais display:none ────────
     Un iframe masqué par display:none voit sa lecture refusée par
     plusieurs navigateurs. On le réduit donc à un pixel transparent
     que rien ne peut cliquer. */
  function construirePlayer(quandPret, siEchec) {
    if (document.getElementById('rbi-yt')) return;

    var hote = document.createElement('div');
    hote.id = 'rbi-yt';
    hote.style.cssText =
      'position:fixed;bottom:0;right:0;width:1px;height:1px;' +
      'opacity:.01;pointer-events:none;z-index:-1;';
    document.body.appendChild(hote);

    var reprise = parseInt(lire(CLE_TEMPS, '0'), 10);

    lecteur = new window.YT.Player('rbi-yt', {
      videoId: VIDEO,
      host: 'https://www.youtube-nocookie.com',
      playerVars: {
        autoplay: 1,
        mute: 1,               // seule façon d'être autorisé à démarrer seul
        controls: 0,
        disablekb: 1,
        fs: 0,
        modestbranding: 1,
        rel: 0,
        playsinline: 1,
        loop: 1,
        playlist: VIDEO,       // exigé par YouTube pour boucler une seule vidéo
        start: reprise > 0 ? reprise : 0
      },
      events: {
        onReady: quandPret,
        onError: siEchec,
        onStateChange: function (e) {
          // Filet de sécurité : certaines vidéos ignorent loop.
          if (e.data === window.YT.PlayerState.ENDED && joue) {
            ecrire(CLE_TEMPS, '0');
            lecteur.playVideo();
          }
        }
      }
    });
  }

  /* ── Fondu : YouTube ne sait pas le faire, on l'écrit ───────────── */
  function fondre(vers, fin) {
    if (fonduEnCours) clearInterval(fonduEnCours);
    if (!lecteur || !lecteur.getVolume) return;

    var depart = lecteur.getVolume();
    var debut = Date.now();

    fonduEnCours = setInterval(function () {
      var avancement = Math.min((Date.now() - debut) / REGLAGES.fondu, 1);
      lecteur.setVolume(depart + (vers - depart) * avancement);
      if (avancement === 1) {
        clearInterval(fonduEnCours);
        fonduEnCours = null;
        if (typeof fin === 'function') fin();
      }
    }, 50);
  }

  /* ── Le premier geste, quel qu'il soit, lève la sourdine ───────── */
  function guetterLePremierGeste() {
    var gestes = ['pointerdown', 'touchstart', 'keydown', 'wheel', 'scroll'];

    function retirer() {
      gestes.forEach(function (g) { window.removeEventListener(g, lever, true); });
    }

    function lever(e) {
      // Un geste porté sur le lecteur lui-même appartient à son bouton.
      // Sans cette réserve, un clic sur « Activer le son » lèverait la
      // sourdine ici, puis le clic serait lu comme une demande d'arrêt :
      // la musique se couperait au moment même où on l'allume.
      if (e && e.target && e.target.nodeType === 1 &&
          boiteLecteur && boiteLecteur.contains(e.target)) return;

      retirer();
      if (!sourdine || !joue) return;
      sourdine = false;
      if (!lecteur || !lecteur.unMute) return;
      lecteur.setVolume(0);
      lecteur.unMute();
      lecteur.playVideo();   // iOS peut avoir refusé le démarrage en sourdine
      fondre(REGLAGES.volume);
      if (majInterface) majInterface();
    }

    gestes.forEach(function (g) {
      window.addEventListener(g, lever, { capture: true, passive: true });
    });
  }

  /* ── Retenir l'endroit du morceau, pour la page suivante ───────── */
  setInterval(function () {
    if (joue && lecteur && lecteur.getCurrentTime) {
      var t = lecteur.getCurrentTime();
      if (t > 0) ecrire(CLE_TEMPS, String(Math.floor(t)));
    }
  }, 5000);

  function arreter() {
    joue = false;
    ecrire(CLE_CHOIX, 'off');
    if (!lecteur) return;
    fondre(0, function () { if (lecteur && lecteur.pauseVideo) lecteur.pauseVideo(); });
  }

  /* ── La place du lecteur ────────────────────────────────────────
     Le lecteur est en position fixe : il flotte AU-DESSUS de la page et
     recouvrait les dernières lignes de texte. On lui réserve donc sa
     place au bas du document, plutôt que de la lui laisser prendre.

     La réserve s'ajoute au remplissage que la page se donne déjà, elle
     ne le remplace pas : écraser le padding d'une feuille de style pour
     y loger le lecteur casserait la mise en page de qui en avait un. */
  var remplissageDorigine = null;
  var surveillant = null;

  function reserverLaPlace() {
    if (!boiteLecteur || !boiteLecteur.isConnected) { libererLaPlace(); return; }

    if (remplissageDorigine === null) {
      remplissageDorigine =
        parseFloat(getComputedStyle(document.body).paddingBottom) || 0;
    }
    // Du haut du lecteur au bas de la fenêtre : c'est exactement la
    // hauteur qu'il occupe, marge du coin comprise. Mesurée plutôt que
    // devinée, elle suit un lecteur qui se replie sur deux lignes.
    var cadre = boiteLecteur.getBoundingClientRect();
    if (!cadre.height) return;
    var occupe = window.innerHeight - cadre.top;
    document.body.style.paddingBottom =
      Math.ceil(remplissageDorigine + occupe + 12) + 'px';
  }

  function libererLaPlace() {
    if (remplissageDorigine === null) return;
    document.body.style.paddingBottom = remplissageDorigine ?
      remplissageDorigine + 'px' : '';
    remplissageDorigine = null;
  }

  function surveillerLaPlace() {
    reserverLaPlace();
    // Le libellé change — « Musique du Rite », « Reprendre », « Couper » —
    // et le cadre se replie autrement sur un téléphone. On remesure
    // plutôt que de figer une hauteur au premier affichage.
    if (window.ResizeObserver && boiteLecteur && !surveillant) {
      surveillant = new ResizeObserver(reserverLaPlace);
      surveillant.observe(boiteLecteur);
    }
    window.addEventListener('resize', reserverLaPlace);
    window.addEventListener('orientationchange', reserverLaPlace);
  }

  /* ── Le lecteur visible ─────────────────────────────────────────── */
  function construireLecteur() {
    if (document.getElementById('music-player')) return;

    var coin = REGLAGES.positionCoin === 'left' ? 'left:1.2rem;' : 'right:1.2rem;';
    var boite = document.createElement('div');
    boite.id = 'music-player';
    boite.style.cssText =
      'position:fixed;bottom:1.2rem;' + coin + 'z-index:999;' +
      'background:rgba(13,13,13,.92);border:1px solid rgba(201,168,76,.4);' +
      'padding:.7rem 1rem;display:flex;align-items:center;gap:.8rem;' +
      'font-family:Georgia,serif;backdrop-filter:blur(6px);' +
      'box-shadow:0 4px 20px rgba(0,0,0,.5);';

    var note = document.createElement('span');
    note.textContent = '♫';
    note.style.cssText = 'font-size:1.05rem;color:#c9a84c;';

    var titre = document.createElement('span');
    titre.style.cssText = 'color:#c9a84c;font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;';

    var bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.style.cssText =
      'background:#c9a84c;border:none;color:#0d0d0d;padding:.3rem .8rem;' +
      'font-size:.75rem;letter-spacing:.1em;text-transform:uppercase;' +
      'font-family:Georgia,serif;cursor:pointer;white-space:nowrap;';

    var fermer = document.createElement('button');
    fermer.type = 'button';
    fermer.textContent = '✕';
    fermer.setAttribute('aria-label', 'Masquer le lecteur');
    fermer.style.cssText = 'background:transparent;border:none;color:#888;font-size:1rem;cursor:pointer;';

    // L'affichage suit trois états : à l'arrêt, en attente d'un geste,
    // et en train de jouer.
    majInterface = function () {
      if (!joue) {
        titre.textContent = 'Musique du Rite';
        bouton.textContent = '▶ Écouter';
        bouton.setAttribute('aria-label', 'Démarrer la musique du Rite');
      } else if (sourdine) {
        titre.textContent = 'Musique du Rite';
        bouton.textContent = '♪ Activer le son';
        bouton.setAttribute('aria-label', 'Activer le son de la musique');
      } else {
        titre.textContent = 'Musique du Rite';
        bouton.textContent = '⏸ Silence';
        bouton.setAttribute('aria-label', 'Arrêter la musique du Rite');
      }
      bouton.disabled = false;
    };

    function indisponible(raison) {
      joue = false;
      titre.textContent = raison;
      bouton.textContent = '—';
      bouton.disabled = true;
      bouton.style.opacity = '.5';
      bouton.style.cursor = 'default';
    }

    function lancer(avecSon) {
      joue = true;
      ecrire(CLE_CHOIX, 'on');

      if (lecteur && lecteur.playVideo) {
        if (avecSon) { sourdine = false; lecteur.setVolume(0); lecteur.unMute(); }
        lecteur.playVideo();
        if (avecSon) fondre(REGLAGES.volume);
        majInterface();
        return;
      }

      bouton.textContent = 'Chargement…';
      bouton.disabled = true;

      chargerAPI(
        function () {
          construirePlayer(
            function () {
              if (!joue) { lecteur.pauseVideo(); majInterface(); return; }
              if (avecSon) {
                sourdine = false;
                lecteur.setVolume(0);
                lecteur.unMute();
                lecteur.playVideo();
                fondre(REGLAGES.volume);
              } else {
                lecteur.mute();
                lecteur.playVideo();
                guetterLePremierGeste();
              }
              majInterface();
            },
            function (e) {
              var code = e && e.data;
              indisponible(code === 101 || code === 150
                ? 'Intégration refusée par la vidéo'
                : 'Musique momentanément indisponible');
            }
          );
        },
        function () { indisponible('Musique momentanément indisponible'); }
      );
    }

    bouton.addEventListener('click', function () {
      if (joue && !sourdine) { arreter(); majInterface(); return; }
      lancer(true);   // un clic sur le bouton est un geste : le son peut sortir
    });

    fermer.addEventListener('click', function () {
      arreter();
      boite.remove();
      // Le lecteur masqué rend sa place : le bas de la page ne doit pas
      // garder un vide dont plus rien ne justifie la présence.
      if (surveillant) { surveillant.disconnect(); surveillant = null; }
      boiteLecteur = null;
      libererLaPlace();
    });

    boite.appendChild(note);
    boite.appendChild(titre);
    boite.appendChild(bouton);
    boite.appendChild(fermer);
    document.body.appendChild(boite);
    boiteLecteur = boite;

    majInterface();
    surveillerLaPlace();

    // Démarrage d'office, sauf si le visiteur a demandé le silence.
    if (lire(CLE_CHOIX, 'on') !== 'off') lancer(false);
  }

  // Une page masquée ne doit pas continuer à sonner dans un onglet oublié.
  document.addEventListener('visibilitychange', function () {
    if (!lecteur || !joue || !lecteur.pauseVideo) return;
    if (document.hidden) lecteur.pauseVideo();
    else lecteur.playVideo();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', construireLecteur);
  } else {
    construireLecteur();
  }
})();
