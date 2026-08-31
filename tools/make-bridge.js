#!/usr/bin/env node
/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — tools/make-bridge.js
   Pont JSON strict entre le site et Make.com.

   ── CONTRAT (invariant, ne jamais l'assouplir) ───────────────
   ENTRÉE  : un unique objet JSON  { action, params?, requestId? }
   SORTIE  : un unique objet JSON  { ok, action, requestId, data|error, meta }
   Rien d'autre n'est jamais écrit sur stdout : ni bannière, ni
   avertissement, ni trace. Make.com applique un JSON.parse brut sur
   le corps reçu ; un seul caractère hors JSON casse tout le scénario.
   Toute la journalisation part donc sur stderr (voir `log()`).

   ── DEUX TRANSPORTS, UN SEUL NOYAU ───────────────────────────
   `dispatch()` ne connaît ni HTTP ni stdin : il reçoit un objet et
   renvoie un objet. Les deux modes ne sont que des adaptateurs :
     • CLI    (défaut)  : stdin → stdout — module « SSH » de Make.com
     • HTTP   (--serve) : POST /bridge  — module « HTTP » / webhook
   Cette séparation permet de tester le noyau sans réseau et garantit
   que les deux transports répondent exactement la même chose.

   ── ZÉRO DÉPENDANCE ──────────────────────────────────────────
   Uniquement des modules natifs Node. Le dépôt est un site statique :
   y introduire des dépendances d'exécution imposerait un `npm install`
   sur le serveur de production, qui n'en a pas besoin aujourd'hui.

   Usage :
     echo '{"action":"ping"}' | node tools/make-bridge.js
     node tools/make-bridge.js --payload '{"action":"site.manifest"}'
     RBI_BRIDGE_TOKEN=xxx node tools/make-bridge.js --serve 8080
════════════════════════════════════════════════════════════════ */
'use strict';

const fs     = require('node:fs');
const path   = require('node:path');
const vm     = require('node:vm');
const http   = require('node:http');
const crypto = require('node:crypto');

const ROOT       = path.resolve(__dirname, '..');
const CONFIG_JS  = path.join(ROOT, 'assets', 'config.js');
const MAX_BODY   = 256 * 1024;   // garde-fou : au-delà, ce n'est plus un appel Make
const VM_TIMEOUT = 1000;         // ms — un fichier de données ne doit jamais boucler

/* Journalisation : stderr EXCLUSIVEMENT. stdout appartient au JSON. */
function log(msg) { process.stderr.write('[rbi-bridge] ' + msg + '\n'); }

/* ── Sérialisation stricte ──────────────────────────────────────
   JSON.stringify transforme silencieusement NaN/Infinity en `null`
   et supprime les `undefined` : Make.com recevrait alors un champ
   manquant sans qu'aucune erreur ne soit levée nulle part. Le
   replacer ci-dessous transforme cette corruption silencieuse en
   échec explicite, détectable en test. */
function toStrictJson(value) {
  return JSON.stringify(value, function (key, val) {
    if (typeof val === 'number' && !Number.isFinite(val)) {
      throw new TypeError('valeur numérique non finie sur « ' + key + ' »');
    }
    if (typeof val === 'bigint' || typeof val === 'function' || typeof val === 'symbol') {
      throw new TypeError('type non sérialisable sur « ' + key + ' »');
    }
    return val;
  });
}

/* ── Analyse stricte de l'entrée ────────────────────────────────
   Le BOM UTF-8 est retiré : certains modules Make.com le placent en
   tête du corps, et JSON.parse le refuse. C'est la SEULE tolérance
   accordée — tout le reste doit être du JSON valide. */
function parseStrict(raw) {
  const text = String(raw).replace(/^﻿/, '').trim();
  if (!text) throw badRequest('E_EMPTY_BODY', 'corps vide : un objet JSON est attendu');
  let obj;
  try { obj = JSON.parse(text); }
  catch (e) { throw badRequest('E_INVALID_JSON', 'JSON invalide : ' + e.message); }
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    throw badRequest('E_NOT_AN_OBJECT', 'la racine doit être un objet JSON');
  }
  return obj;
}

/* Erreur porteuse d'un code stable : Make.com route ses scénarios sur
   `error.code`, jamais sur le message (qui reste humain et traduisible). */
function badRequest(code, message, details) {
  const e = new Error(message);
  e.rbiCode = code;
  e.rbiDetails = details || null;
  e.rbiStatus = 400;
  return e;
}

/* ── Lecture de la configuration du site ────────────────────────
   assets/config.js est la source de vérité du contenu. Plutôt que
   d'en dupliquer une copie JSON — qui divergerait au premier
   changement — on ÉVALUE le fichier dans un contexte `vm` isolé :
     • pas de `require`, pas de `process`, pas de `fs` exposés ;
     • timeout dur contre une boucle accidentelle ;
     • le contexte est jeté après lecture.
   Le fichier ne contient que des littéraux, cette exécution est donc
   déterministe et sans effet de bord. */
let _configCache = null;
function loadConfig() {
  if (_configCache) return _configCache;
  let source;
  try { source = fs.readFileSync(CONFIG_JS, 'utf8'); }
  catch (e) {
    const err = new Error('assets/config.js illisible : ' + e.message);
    err.rbiCode = 'E_CONFIG_UNREADABLE'; err.rbiStatus = 500;
    throw err;
  }
  const sandbox = { window: {} };
  try {
    vm.runInNewContext(source, sandbox, { timeout: VM_TIMEOUT, filename: 'config.js' });
  } catch (e) {
    const err = new Error('assets/config.js non évaluable : ' + e.message);
    err.rbiCode = 'E_CONFIG_INVALID'; err.rbiStatus = 500;
    throw err;
  }
  const cfg = sandbox.RBI_CONFIG || sandbox.window.RBI_CONFIG;
  if (!cfg || typeof cfg !== 'object') {
    const err = new Error('RBI_CONFIG absent de assets/config.js');
    err.rbiCode = 'E_CONFIG_MISSING'; err.rbiStatus = 500;
    throw err;
  }
  /* Copie profonde par aller-retour JSON : le reste du programme ne
     peut plus muter l'objet évalué, et l'on vérifie du même coup que
     la config est intégralement sérialisable en JSON strict. */
  _configCache = JSON.parse(toStrictJson(cfg));
  return _configCache;
}

/* ── Normalisation partagée avec le site ────────────────────────
   RÉPLIQUE EXACTE de `normalise()` dans assets/app.js. Duplication
   assumée et documentée des deux côtés : le navigateur ne peut pas
   charger un module Node, et Node ne peut pas charger app.js (IIFE
   qui touche au DOM). Toute modification ici doit être reportée là-bas,
   sans quoi le verdict du serveur et celui de la page divergeraient. */
function normalise(str) {
  return (str || '')
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/* ═══════════════════════════════════════════════════════════════
   ACTIONS
   Une fonction pure par action : (params, ctx) → data.
   Aucune n'écrit sur disque ni sur le réseau : ce pont est en
   lecture seule. Un scénario Make.com peut donc être rejoué sans
   risque, et le pont être exposé sans crainte d'effet de bord.
════════════════════════════════════════════════════════════════ */
const ACTIONS = {

  /* Sonde de disponibilité — utilisée par le test de fumée CI et par
     le module « HTTP » de Make.com pour valider la connexion. */
  'ping': function () {
    return { pong: true, service: 'rbi-make-bridge', version: '1.0.0' };
  },

  /* Inventaire du site : ce que Make.com peut demander ensuite. */
  'site.manifest': function () {
    const c = loadConfig();
    return {
      sections: Object.keys(c),
      chefs:    (c.chefs   && c.chefs.membres  || []).length,
      livres:   (c.livres  && c.livres.liste   || []).length,
      questions:(c.tuilage && c.tuilage.questions || []).length,
      documents:(c.tuilage && c.tuilage.pdfs   || []).length,
      contact:  { email: c.contact && c.contact.email || null }
    };
  },

  /* Lecture ciblée du contenu.
     `path` est un chemin pointé (« chefs.membres.0.nom »). On refuse
     explicitement les segments hérités du prototype : sans ce filtre,
     un `params.path` malveillant venant d'un webhook pourrait
     atteindre `__proto__` ou `constructor` et faire fuiter autre
     chose que du contenu éditorial. */
  'content.get': function (params) {
    const cfg = loadConfig();
    const p = params.path;
    if (p === undefined || p === null || p === '') return cfg;
    if (typeof p !== 'string') throw badRequest('E_BAD_PARAM', '« path » doit être une chaîne');

    const INTERDITS = ['__proto__', 'prototype', 'constructor'];
    let node = cfg;
    const segments = p.split('.');
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      if (INTERDITS.indexOf(seg) !== -1) {
        throw badRequest('E_FORBIDDEN_PATH', 'segment interdit : ' + seg);
      }
      if (node === null || typeof node !== 'object' || !Object.prototype.hasOwnProperty.call(node, seg)) {
        throw badRequest('E_PATH_NOT_FOUND', 'chemin introuvable : ' + p, { segment: seg });
      }
      node = node[seg];
    }
    return { path: p, value: node };
  },

  /* Vérification de tuilage côté serveur.
     ⚠ Ne transforme PAS le tuilage en contrôle d'accès : les réponses
     restent publiques dans config.js (voir assets/app.js §6). Cette
     action sert à faire trancher un scénario Make.com (formulaire,
     e-mail, chatbot) par la MÊME logique que la page, pas à protéger
     quoi que ce soit.
     Le détail par question n'expose jamais la bonne réponse : un
     appelant ne peut donc pas s'en servir comme oracle d'énumération
     plus efficacement qu'en lisant config.js directement. */
  'tuilage.verify': function (params) {
    const cfg = loadConfig();
    const questions = (cfg.tuilage && cfg.tuilage.questions) || [];
    const fournies = params.answers;
    if (fournies === null || typeof fournies !== 'object') {
      throw badRequest('E_BAD_PARAM', '« answers » doit être un objet { id: réponse } ou un tableau');
    }
    /* Les deux formes sont acceptées — tableau positionnel ou objet
       indexé par id — parce que Make.com produit tantôt l'une (mapping
       d'un itérateur) tantôt l'autre (mapping nommé d'un formulaire). */
    const parId = Array.isArray(fournies)
      ? questions.reduce(function (acc, q, i) { acc[q.id] = fournies[i]; return acc; }, {})
      : fournies;

    const details = questions.map(function (q) {
      const brut = parId[q.id];
      const val  = normalise(typeof brut === 'string' ? brut : '');
      const ok   = val !== '' && (q.reponses || []).some(function (r) { return normalise(r) === val; });
      return { id: q.id, question: q.texte, fournie: typeof brut === 'string' ? brut : null, valide: ok };
    });

    const reconnu = details.length > 0 && details.every(function (d) { return d.valide; });
    return {
      reconnu: reconnu,
      message: reconnu ? (cfg.tuilage.succes && cfg.tuilage.succes.message) || ''
                       : (cfg.tuilage.echec  && cfg.tuilage.echec.message)  || '',
      details: details
    };
  },

  /* Normalisation d'une demande entrante (formulaire, e-mail parsé).
     Le pont VALIDE et NORMALISE, il n'envoie rien : l'acheminement
     (e-mail, tableur, CRM) reste l'affaire du scénario Make.com. Cette
     frontière évite d'enfermer une politique métier dans le dépôt du
     site, où elle serait invisible pour la personne qui l'exploite. */
  'contact.normalize': function (params) {
    const src = params.payload;
    if (src === null || typeof src !== 'object' || Array.isArray(src)) {
      throw badRequest('E_BAD_PARAM', '« payload » doit être un objet');
    }
    const texte = function (v, max) {
      return String(v === undefined || v === null ? '' : v).replace(/\s+/g, ' ').trim().slice(0, max || 500);
    };
    const record = {
      nom:     texte(src.nom || src.name || src.lastname, 120),
      prenom:  texte(src.prenom || src.firstname, 120),
      email:   texte(src.email, 254).toLowerCase(),
      sujet:   texte(src.sujet || src.subject, 200),
      message: texte(src.message || src.body, 4000),
      source:  texte(src.source, 60) || 'make.com'
    };
    /* Validation d'e-mail volontairement permissive : la seule preuve
       d'une adresse est un envoi réussi. Un motif strict (RFC 5322)
       rejetterait des adresses légitimes — un faux négatif coûte ici
       un adhérent perdu, un faux positif coûte un e-mail en échec. */
    const erreurs = [];
    if (!record.nom && !record.prenom) erreurs.push('nom ou prénom requis');
    if (!/^[^@\s]+@[^@\s.]+\.[^@\s]+$/.test(record.email)) erreurs.push('email invalide');
    if (!record.message) erreurs.push('message vide');

    return {
      valide: erreurs.length === 0,
      erreurs: erreurs,
      record: record,
      destinataire: (loadConfig().contact || {}).email || null
    };
  }
};

/* ═══════════════════════════════════════════════════════════════
   NOYAU — indépendant du transport
════════════════════════════════════════════════════════════════ */
function dispatch(requete) {
  const debut = Date.now();
  const action = requete.action;
  const requestId = typeof requete.requestId === 'string' ? requete.requestId : null;
  const enveloppe = function (corps) {
    corps.action = typeof action === 'string' ? action : null;
    corps.requestId = requestId;
    corps.meta = { durationMs: Date.now() - debut, at: new Date().toISOString() };
    return corps;
  };

  if (typeof action !== 'string' || !action) {
    return enveloppe({ ok: false, error: { code: 'E_MISSING_ACTION', message: '« action » est requis', details: { available: Object.keys(ACTIONS) } } });
  }
  if (!Object.prototype.hasOwnProperty.call(ACTIONS, action)) {
    return enveloppe({ ok: false, error: { code: 'E_UNKNOWN_ACTION', message: 'action inconnue : ' + action, details: { available: Object.keys(ACTIONS) } } });
  }
  const params = (requete.params === undefined || requete.params === null) ? {} : requete.params;
  if (typeof params !== 'object' || Array.isArray(params)) {
    return enveloppe({ ok: false, error: { code: 'E_BAD_PARAMS', message: '« params » doit être un objet', details: null } });
  }
  try {
    return enveloppe({ ok: true, data: ACTIONS[action](params) });
  } catch (e) {
    log(action + ' → ' + (e.rbiCode || 'E_INTERNAL') + ' : ' + e.message);
    return enveloppe({
      ok: false,
      error: {
        code: e.rbiCode || 'E_INTERNAL',
        /* Message d'erreur interne masqué : une exception inattendue
           peut contenir un chemin absolu du serveur. Les codes métier
           (rbiCode) sont, eux, rédigés pour être lus par l'appelant. */
        message: e.rbiCode ? e.message : 'erreur interne',
        details: e.rbiDetails || null
      }
    });
  }
}

/* ── Transport 1 : CLI (stdin → stdout) ─────────────────────────
   Code de sortie 0 même en cas d'erreur métier, par défaut : le
   module « SSH » de Make.com abandonne le scénario sur un code non
   nul et n'en lit alors pas la sortie — la réponse d'erreur, pourtant
   exploitable, serait perdue. `--strict-exit` rétablit le code 1 pour
   un usage en script shell ou en CI. */
function runCli(argv) {
  const strictExit = argv.indexOf('--strict-exit') !== -1;
  const iPayload = argv.indexOf('--payload');
  const emettre = function (reponse) {
    process.stdout.write(toStrictJson(reponse) + '\n');
    if (strictExit && !reponse.ok) process.exitCode = 1;
  };
  const traiter = function (brut) {
    let reponse;
    try { reponse = dispatch(parseStrict(brut)); }
    catch (e) {
      reponse = { ok: false, action: null, requestId: null,
                  error: { code: e.rbiCode || 'E_INTERNAL', message: e.message, details: e.rbiDetails || null },
                  meta: { durationMs: 0, at: new Date().toISOString() } };
    }
    emettre(reponse);
  };

  if (iPayload !== -1) return traiter(argv[iPayload + 1] || '');

  /* Lecture intégrale de stdin avant traitement : la requête est un
     document JSON unique, la traiter par fragments n'aurait aucun sens.
     Le plafond MAX_BODY protège d'un flux qui ne se fermerait pas. */
  let brut = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', function (c) {
    brut += c;
    if (brut.length > MAX_BODY) {
      emettre({ ok: false, action: null, requestId: null,
                error: { code: 'E_BODY_TOO_LARGE', message: 'corps > ' + MAX_BODY + ' octets', details: null },
                meta: { durationMs: 0, at: new Date().toISOString() } });
      process.exit(strictExit ? 1 : 0);
    }
  });
  process.stdin.on('end', function () { traiter(brut); });
}

/* ── Transport 2 : HTTP (webhook Make.com) ──────────────────────
   Surface volontairement minimale : une seule route, une seule
   méthode, un seul type de contenu. Tout le reste est refusé avant
   d'atteindre le noyau. */
function runServer(port) {
  const token = process.env.RBI_BRIDGE_TOKEN || '';
  /* Refus de démarrer sans jeton : un pont ouvert exposerait le
     contenu et la vérification de tuilage à n'importe qui. Échouer au
     démarrage est préférable à un démarrage discrètement non protégé. */
  if (token.length < 16) {
    log('RBI_BRIDGE_TOKEN manquant ou trop court (16 caractères minimum) — démarrage refusé');
    process.exit(2);
  }
  const attendu = Buffer.from(token);

  const serveur = http.createServer(function (req, res) {
    const repondre = function (statut, corps) {
      const texte = toStrictJson(corps);
      res.writeHead(statut, {
        'content-type': 'application/json; charset=utf-8',
        'content-length': Buffer.byteLength(texte),
        'cache-control': 'no-store'
      });
      res.end(texte);
    };
    const echec = function (statut, code, message) {
      repondre(statut, { ok: false, action: null, requestId: null,
                         error: { code: code, message: message, details: null },
                         meta: { durationMs: 0, at: new Date().toISOString() } });
    };

    if (req.method !== 'POST')                     return echec(405, 'E_METHOD_NOT_ALLOWED', 'POST uniquement');
    if ((req.url || '').split('?')[0] !== '/bridge') return echec(404, 'E_NOT_FOUND', 'route inconnue');

    /* Comparaison à temps constant : `===` sur une chaîne s'arrête au
       premier caractère différent et laisse fuir la longueur du préfixe
       correct, ce qui rend le jeton devinable octet par octet. */
    const fourni = Buffer.from(String(req.headers['x-rbi-token'] || ''));
    if (fourni.length !== attendu.length || !crypto.timingSafeEqual(fourni, attendu)) {
      return echec(401, 'E_UNAUTHORIZED', 'jeton invalide');
    }

    let brut = '';
    let coupe = false;
    req.setEncoding('utf8');
    req.on('data', function (c) {
      if (coupe) return;
      brut += c;
      if (brut.length > MAX_BODY) { coupe = true; req.destroy(); echec(413, 'E_BODY_TOO_LARGE', 'corps > ' + MAX_BODY + ' octets'); }
    });
    req.on('end', function () {
      if (coupe) return;
      let reponse;
      try { reponse = dispatch(parseStrict(brut)); }
      catch (e) {
        return echec(e.rbiStatus || 400, e.rbiCode || 'E_INTERNAL', e.message);
      }
      /* 200 même sur `ok:false` métier : le code HTTP décrit le
         transport, l'enveloppe décrit le métier. Make.com peut ainsi
         router sur `ok` sans traiter chaque refus comme une panne. */
      repondre(200, reponse);
    });
  });

  serveur.listen(port, function () { log('écoute sur http://127.0.0.1:' + port + '/bridge'); });
}

/* ── Point d'entrée ─────────────────────────────────────────── */
if (require.main === module) {
  const argv = process.argv.slice(2);
  const iServe = argv.indexOf('--serve');
  if (iServe !== -1) runServer(parseInt(argv[iServe + 1], 10) || 8080);
  else runCli(argv);
}

/* Export du noyau pour les tests : ils appellent `dispatch()`
   directement, sans transport, donc sans port ni processus fils. */
module.exports = { dispatch: dispatch, parseStrict: parseStrict, toStrictJson: toStrictJson, normalise: normalise, ACTIONS: ACTIONS };
