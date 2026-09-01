/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — musique du Rite

   Remplace le lecteur YouTube qui équipait les pages. Celui-ci
   dépendait d'une vidéo tierce susceptible de disparaître, chargeait
   l'API de YouTube et ses traceurs sur chaque page, et imposait une
   musique qu'on ne maîtrisait pas.

   Ici, rien n'est chargé : le son est synthétisé par le navigateur.
   Pas de fichier, pas de requête, pas de cookie, pas de question de
   droits — et une matière sonore accordée au site.

   ── Ce qui est joué ────────────────────────────────────────────
   Un bourdon grave sur ré et sa quinte, et par-dessus, des notes
   espacées prises dans le mode Ahava Rabbah (ré, mi♭, fa♯, sol, la,
   si♭, do) — le mode hébraïque de la seconde augmentée. Le tempo est
   volontairement indéterminé : deux visites ne s'entendent jamais
   pareil.

   ── Réglages ───────────────────────────────────────────────────
   Tout se modifie dans REGLAGES ci-dessous.

   ── Usage ──────────────────────────────────────────────────────
   Inclure <script src="assets/musique.js"></script> avant la
   fermeture du <body>. Le lecteur se construit tout seul. Le son ne
   démarre jamais sans un clic : les navigateurs l'interdisent, et
   c'est heureux.
════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var REGLAGES = {
    volume:        0.42,   // volume général, de 0 à 1
    fondu:         1.6,    // secondes de fondu à l'ouverture et à la fermeture
    ecartMin:      2.2,    // délai minimum entre deux notes, en secondes
    ecartMax:      5.5,    // délai maximum
    dureeNote:     5.5,    // longueur d'une note, résonance comprise
    positionCoin:  'right' // 'right' ou 'left'
  };

  // Mode Ahava Rabbah sur ré, en hertz.
  //
  // Deux octaves médium-aigu, et non l'octave grave d'origine : un
  // haut-parleur de téléphone ou d'ordinateur portable ne restitue
  // pratiquement rien sous 200 Hz. Une musique écrite dans les graves
  // profonds y est jouée sans être entendue.
  var MODE = [
    293.66, 311.13, 369.99, 392.00, 440.00, 466.16, 523.25,
    587.33, 622.25, 739.99, 783.99, 880.00, 932.33, 1046.50
  ];

  var ctx = null, maitre = null, bourdon = [], minuterie = null, joue = false;

  /* ── Le bourdon : trois voix légèrement désaccordées ─────────── */
  function construireBourdon() {
    var filtre = ctx.createBiquadFilter();
    filtre.type = 'lowpass';
    filtre.frequency.value = 1400;
    filtre.Q.value = 0.7;
    filtre.connect(maitre);

    // Une oscillation très lente sur la coupure du filtre : c'est elle
    // qui donne au bourdon sa respiration, sans quoi il serait figé.
    var souffle = ctx.createOscillator();
    var ampleur = ctx.createGain();
    souffle.frequency.value = 0.045;
    ampleur.gain.value = 550;
    souffle.connect(ampleur).connect(filtre.frequency);
    souffle.start();

    // Ré, la, ré — une octave plus haut que la basse d'orgue qu'on
    // aurait choisie pour une écoute au casque. C'est le registre que
    // les petites enceintes savent réellement produire.
    [146.83, 220.00, 293.66].forEach(function (f, i) {
      var osc = ctx.createOscillator();
      osc.type = i === 0 ? 'sine' : 'triangle';
      osc.frequency.value = f;
      osc.detune.value = (i - 1) * 4;          // battements lents entre les voix

      var g = ctx.createGain();
      g.gain.value = [0.42, 0.26, 0.16][i];

      osc.connect(g).connect(filtre);
      osc.start();
      bourdon.push(osc);
    });

    bourdon.push(souffle);
  }

  /* ── Une note : cloche douce, longue résonance ───────────────── */
  function jouerNote() {
    if (!joue) return;

    // Onglet masqué : le contexte est suspendu et son horloge est figée.
    // Programmer des notes maintenant les ferait toutes tomber au même
    // instant, et éclater d'un coup au retour. On repasse plus tard.
    if (ctx.state !== 'running') {
      minuterie = setTimeout(jouerNote, 2000);
      return;
    }

    var f = MODE[Math.floor(Math.random() * MODE.length)];
    var t = ctx.currentTime;
    var duree = REGLAGES.dureeNote * (0.75 + Math.random() * 0.5);

    var osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = f;

    // Une quinte à peine audible sous la note, pour l'épaissir.
    var quinte = ctx.createOscillator();
    quinte.type = 'sine';
    quinte.frequency.value = f * 1.5;

    var gQuinte = ctx.createGain();
    gQuinte.gain.value = 0.26;

    var env = ctx.createGain();
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(0.30, t + 0.5);
    env.gain.exponentialRampToValueAtTime(0.0001, t + duree);

    // Chaque note se pose ailleurs dans l'espace stéréo.
    var pano = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (pano) pano.pan.value = (Math.random() - 0.5) * 0.7;

    osc.connect(env);
    quinte.connect(gQuinte).connect(env);
    if (pano) { env.connect(pano).connect(maitre); } else { env.connect(maitre); }

    osc.start(t);   quinte.start(t);
    osc.stop(t + duree + 0.2);
    quinte.stop(t + duree + 0.2);

    var attente = REGLAGES.ecartMin + Math.random() * (REGLAGES.ecartMax - REGLAGES.ecartMin);
    minuterie = setTimeout(jouerNote, attente * 1000);
  }

  function demarrer() {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return false;

    if (!ctx) {
      ctx = new Ctx();
      maitre = ctx.createGain();
      maitre.gain.value = 0.0001;
      maitre.connect(ctx.destination);
      construireBourdon();
    }
    // ── Déverrouillage iOS ──────────────────────────────────────
    // Sur iPhone et iPad, le son reste muet tant qu'aucun échantillon
    // n'a été joué à l'intérieur même du geste de l'utilisateur. Un
    // souffle inaudible d'un millième de seconde suffit à lever le
    // verrou ; sans lui, le bouton semble ne rien faire.
    try {
      var vide = ctx.createBuffer(1, 1, 22050);
      var lecteur = ctx.createBufferSource();
      lecteur.buffer = vide;
      lecteur.connect(ctx.destination);
      lecteur.start(0);
    } catch (e) { /* sans importance si le navigateur refuse */ }

    if (ctx.state !== 'running') ctx.resume();

    joue = true;
    maitre.gain.cancelScheduledValues(ctx.currentTime);
    maitre.gain.setValueAtTime(Math.max(maitre.gain.value, 0.0001), ctx.currentTime);
    maitre.gain.exponentialRampToValueAtTime(REGLAGES.volume, ctx.currentTime + REGLAGES.fondu);

    minuterie = setTimeout(jouerNote, 1200);
    return true;
  }

  function arreter() {
    joue = false;
    if (minuterie) { clearTimeout(minuterie); minuterie = null; }
    if (!ctx) return;
    maitre.gain.cancelScheduledValues(ctx.currentTime);
    maitre.gain.setValueAtTime(maitre.gain.value, ctx.currentTime);
    maitre.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + REGLAGES.fondu * 0.6);
  }

  /* ── Le lecteur ──────────────────────────────────────────────── */
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
      'font-family:Georgia,serif;cursor:pointer;';

    var fermer = document.createElement('button');
    fermer.type = 'button';
    fermer.textContent = '✕';
    fermer.setAttribute('aria-label', 'Masquer le lecteur');
    fermer.style.cssText = 'background:transparent;border:none;color:#888;font-size:1rem;cursor:pointer;';

    bouton.addEventListener('click', function () {
      if (joue) {
        arreter();
        bouton.textContent = '▶ Écouter';
        bouton.setAttribute('aria-label', 'Démarrer la musique du Rite');
      } else if (demarrer()) {
        bouton.textContent = '⏸ Silence';
        bouton.setAttribute('aria-label', 'Arrêter la musique du Rite');

        // Si le navigateur a refusé de démarrer, le bouton afficherait
        // « Silence » sans qu'aucun son ne sorte. On vérifie, et on le dit.
        setTimeout(function () {
          if (joue && ctx && ctx.state !== 'running') {
            titre.textContent = 'Son bloqué par le navigateur';
            titre.title = "Sur iPhone, vérifiez que le mode silencieux n'est pas activé.";
          }
        }, 800);
      } else {
        titre.textContent = 'Son indisponible ici';
        bouton.textContent = '—';
        bouton.disabled = true;
        bouton.style.opacity = '.5';
        bouton.style.cursor = 'default';
      }
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
    if (document.hidden && ctx && joue) ctx.suspend();
    else if (!document.hidden && ctx && joue) ctx.resume();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', construireLecteur);
  } else {
    construireLecteur();
  }
})();
