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

   ── Ce qui protège les visiteurs ───────────────────────────────
   1. Rien n'est chargé tant que personne ne clique. Tant que le
      bouton n'est pas actionné, aucune requête ne part vers Google
      et aucun traceur n'est déposé. Un visiteur qui ne veut pas de
      musique n'est jamais vu par YouTube.
   2. Le lecteur est celui de youtube-nocookie.com, qui ne dépose
      pas de cookie publicitaire.

   ── Réglages ───────────────────────────────────────────────────
   Tout se modifie dans REGLAGES ci-dessous. Pour changer de
   morceau, remplacer VIDEO par l'identifiant de la nouvelle vidéo —
   les onze caractères qui suivent « youtu.be/ » ou « ?v= ».

   ── Usage ──────────────────────────────────────────────────────
   Inclure <script src="assets/musique.js?v=20260901b"></script>
   avant la fermeture du <body>. Le numéro de version n'est pas
   décoratif : _headers conserve les fichiers d'assets un an, et
   c'est le changement d'adresse qui force les navigateurs à
   reprendre la nouvelle version. Modifier ce fichier sans changer
   le numéro revient à ne rien publier du tout.

   Le son ne démarre jamais sans un clic : les navigateurs
   l'interdisent, et c'est heureux.
════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // Les onze caractères qui identifient la vidéo.
  var VIDEO = '_pGXBoOsrJI';

  var REGLAGES = {
    volume:       35,      // volume final, de 0 à 100
    fondu:        2500,    // durée du fondu d'ouverture et de fermeture, en ms
    positionCoin: 'right'  // 'right' ou 'left'
  };

  var lecteur = null;      // l'objet YT.Player
  var joue = false;
  var fonduEnCours = null;
  var apiDemandee = false;

  /* ── Chargement de l'API, une seule fois, et seulement sur clic ── */
  function chargerAPI(quandPrete, siEchec) {
    if (window.YT && window.YT.Player) { quandPrete(); return; }

    // Une autre page a pu lancer le chargement : on s'y raccroche.
    if (!apiDemandee) {
      apiDemandee = true;
      var s = document.createElement('script');
      s.src = 'https://www.youtube.com/iframe_api';
      s.onerror = siEchec;
      document.head.appendChild(s);
    }

    // L'API prévient par une fonction globale, qu'on n'écrase pas si
    // elle existe déjà.
    var precedent = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function () {
      if (typeof precedent === 'function') precedent();
      quandPrete();
    };

    // Réseau coupé, extension qui bloque, API qui ne répond pas :
    // sans garde-fou le bouton resterait figé sur « Chargement… ».
    setTimeout(function () {
      if (!window.YT || !window.YT.Player) siEchec();
    }, 8000);
  }

  /* ── Le lecteur : un point invisible, jamais display:none ────────
     Un iframe caché par display:none voit sa lecture refusée par
     plusieurs navigateurs. On le réduit donc à un pixel transparent
     que rien ne peut cliquer. */
  function construirePlayer(quandPret, siEchec) {
    var hote = document.createElement('div');
    hote.id = 'rbi-yt';
    hote.style.cssText =
      'position:fixed;bottom:0;right:0;width:1px;height:1px;' +
      'opacity:.01;pointer-events:none;z-index:-1;';
    document.body.appendChild(hote);

    lecteur = new window.YT.Player('rbi-yt', {
      videoId: VIDEO,
      host: 'https://www.youtube-nocookie.com',
      playerVars: {
        autoplay: 1,
        controls: 0,
        disablekb: 1,
        fs: 0,
        modestbranding: 1,
        rel: 0,
        playsinline: 1,
        loop: 1,
        playlist: VIDEO   // exigé par YouTube pour boucler une seule vidéo
      },
      events: {
        onReady: quandPret,
        onError: siEchec,
        onStateChange: function (e) {
          // Filet de sécurité : certaines vidéos ignorent loop.
          if (e.data === window.YT.PlayerState.ENDED && joue) lecteur.playVideo();
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

  function arreter() {
    joue = false;
    if (!lecteur) return;
    fondre(0, function () { if (lecteur && lecteur.pauseVideo) lecteur.pauseVideo(); });
  }

  /* ── Le lecteur visible ─────────────────────────────────────────── */
  function construireLecteur() {
    if (document.getElementById('music-player')) return; // déjà en place

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
    titre.textContent = 'Musique du Rite';
    titre.style.cssText = 'color:#c9a84c;font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;';

    var bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.textContent = '▶ Écouter';
    bouton.setAttribute('aria-label', 'Démarrer la musique du Rite');
    bouton.style.cssText =
      'background:#c9a84c;border:none;color:#0d0d0d;padding:.3rem .8rem;' +
      'font-size:.75rem;letter-spacing:.1em;text-transform:uppercase;' +
      'font-family:Georgia,serif;cursor:pointer;white-space:nowrap;';

    var fermer = document.createElement('button');
    fermer.type = 'button';
    fermer.textContent = '✕';
    fermer.setAttribute('aria-label', 'Masquer le lecteur');
    fermer.style.cssText = 'background:transparent;border:none;color:#888;font-size:1rem;cursor:pointer;';

    function enEcoute() {
      bouton.textContent = '⏸ Silence';
      bouton.setAttribute('aria-label', 'Arrêter la musique du Rite');
      bouton.disabled = false;
      titre.textContent = 'Musique du Rite';
    }

    function auRepos() {
      bouton.textContent = '▶ Écouter';
      bouton.setAttribute('aria-label', 'Démarrer la musique du Rite');
      bouton.disabled = false;
    }

    function indisponible(raison) {
      joue = false;
      titre.textContent = raison;
      bouton.textContent = '—';
      bouton.disabled = true;
      bouton.style.opacity = '.5';
      bouton.style.cursor = 'default';
    }

    bouton.addEventListener('click', function () {
      if (joue) { arreter(); auRepos(); return; }

      joue = true;

      // Deuxième écoute et suivantes : le lecteur existe déjà.
      if (lecteur && lecteur.playVideo) {
        lecteur.setVolume(0);
        lecteur.playVideo();
        fondre(REGLAGES.volume);
        enEcoute();
        return;
      }

      bouton.textContent = 'Chargement…';
      bouton.disabled = true;

      chargerAPI(
        function () {
          construirePlayer(
            function () {
              if (!joue) { lecteur.pauseVideo(); auRepos(); return; }
              lecteur.setVolume(0);
              lecteur.playVideo();
              fondre(REGLAGES.volume);
              enEcoute();
            },
            function (e) {
              // 101 et 150 : le propriétaire interdit l'intégration.
              var code = e && e.data;
              indisponible(code === 101 || code === 150
                ? 'Intégration refusée par la vidéo'
                : 'Musique momentanément indisponible');
            }
          );
        },
        function () { indisponible('Musique momentanément indisponible'); }
      );
    });

    fermer.addEventListener('click', function () {
      arreter();
      boite.remove();
    });

    boite.appendChild(note);
    boite.appendChild(titre);
    boite.appendChild(bouton);
    boite.appendChild(fermer);
    document.body.appendChild(boite);
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
