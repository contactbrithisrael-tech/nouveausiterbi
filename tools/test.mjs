/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — tools/test.mjs
   Tests statiques et unitaires — sans navigateur, sans réseau.

   ── POURQUOI DEUX SUITES SÉPARÉES ────────────────────────────
   Celle-ci s'exécute en moins d'une seconde et ne dépend de rien :
   elle peut donc tourner à chaque commit, en local comme en CI.
   Le parcours navigateur (tools/smoke-test.mjs) coûte un
   téléchargement de Chromium et plusieurs secondes ; il reste utile
   mais ne doit pas être le seul filet, sous peine d'être désactivé
   le jour où il devient lent.

   ── CE QUI EST VÉRIFIÉ ───────────────────────────────────────
   1. Syntaxe de tout le JavaScript livré (y compris inline).
   2. Validité du JSON-LD — une erreur y est invisible à l'œil et
      supprime silencieusement le référencement enrichi.
   3. Contrat du pont Make.com : enveloppe, codes d'erreur, refus
      des chemins dangereux, sérialisation stricte.
   4. Cohérence config ↔ code : les `id` référencés par config.js
      doivent exister dans les fichiers qui les consomment.
════════════════════════════════════════════════════════════════ */
import { readFile, readdir } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const exec = promisify(execFile);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require_ = createRequire(import.meta.url);

let passes = 0;
const echecs = [];
const avertissements = [];

/* Assertions minimalistes plutôt que node:test ou un framework :
   la sortie doit rester lisible dans un journal CI brut, et la suite
   ne doit imposer aucune dépendance pour pouvoir être lancée sur une
   machine vierge. */
function ok(condition, titre, detail) {
  if (condition) { passes++; console.log('  ✓ ' + titre); }
  else { echecs.push({ titre, detail: detail ?? '' }); console.log('  ✗ ' + titre + (detail ? ' — ' + detail : '')); }
}
function section(titre) { console.log('\n▸ ' + titre); }

/* Avertissement : constat exact mais NON bloquant. Distinguer les deux
   est ce qui garde une suite de tests crédible — une CI qui échoue sur
   un média manquant (que le site sait afficher en placeholder) finit
   par être ignorée, et masque alors les vraies régressions. */
function avertir(titre, detail) { avertissements.push({ titre, detail: detail ?? '' }); console.log('  ! ' + titre + (detail ? ' — ' + detail : '')); }

async function listerFichiers(dir, filtre, exclus = new Set(['.git', 'node_modules', 'dist'])) {
  const out = [];
  for (const e of await readdir(dir, { withFileTypes: true })) {
    if (exclus.has(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await listerFichiers(p, filtre, exclus));
    else if (filtre(e.name)) out.push(p);
  }
  return out;
}

/* Périmètre des tests : le JavaScript RÉELLEMENT LIVRÉ, c'est-à-dire
   celui qu'une balise <script> d'une page charge, plus l'outillage.
   Définir le périmètre par les références plutôt que par l'extension
   évite deux travers symétriques : bloquer la CI sur des copies mortes
   laissées à la racine (elles ne sont servies à personne), et laisser
   passer un fichier cassé sous prétexte qu'il est rangé ailleurs.
   Ce qui n'est référencé nulle part n'est pas ignoré pour autant : il
   ressort en avertissement, en fin de suite. */
/* Le balisage est TOUJOURS analysé commentaires retirés. Ces fichiers
   sont abondamment commentés et un commentaire cite le code qu'il
   explique : une phrase mentionnant « <script> » serait sinon analysée
   comme un vrai script, et ferait échouer la suite sur de la prose. */
function sansCommentaires(html) { return html.replace(/<!--[\s\S]*?-->/g, ''); }

async function fichiersLivres() {
  const pages = await listerFichiers(ROOT, n => n.endsWith('.html'), new Set(['.git', 'node_modules', 'dist', 'backup']));
  const references = new Set();
  for (const page of pages) {
    const html = sansCommentaires(await readFile(page, 'utf8'));
    for (const m of html.matchAll(/<script[^>]*\bsrc="([^"]+\.js)"/gi)) {
      if (/^https?:/i.test(m[1])) continue;   // dépendance tierce : hors périmètre
      references.add(path.resolve(path.dirname(page), m[1]));
    }
  }
  const outils = await listerFichiers(path.join(ROOT, 'tools'), n => n.endsWith('.js') || n.endsWith('.mjs'));
  return { livres: [...references].sort(), outils, pages };
}

/* ── 1. Syntaxe JavaScript ──────────────────────────────────── */
async function testSyntaxe() {
  section('Syntaxe JavaScript (fichiers livrés + outillage)');
  const { livres, outils, pages } = await fichiersLivres();
  for (const f of [...livres, ...outils]) {
    try { await exec(process.execPath, ['--check', f]); ok(true, path.relative(ROOT, f)); }
    catch (e) { ok(false, path.relative(ROOT, f), (e.stderr || e.message).split('\n')[0]); }
  }

  /* Copies non référencées : signalées, jamais bloquantes. Elles
     alourdissent le déploiement et peuvent diverger du fichier servi —
     c'est une dette à connaître, pas une panne. */
  const tous = await listerFichiers(ROOT, n => n.endsWith('.js'), new Set(['.git', 'node_modules', 'dist', 'tools']));
  for (const f of tous) {
    if (livres.includes(f)) continue;
    const rel = path.relative(ROOT, f);
    let valide = true;
    try { await exec(process.execPath, ['--check', f]); } catch { valide = false; }
    avertir(`${rel} — non référencé par aucune page${valide ? '' : ' ET syntaxiquement invalide'}`);
  }

  /* Le JS inline des pages est du code livré comme un autre : il
     échappe pourtant à tout outil qui ne regarde que les .js. On
     l'extrait donc pour le contrôler explicitement. */
  for (const page of pages) {
    const html = sansCommentaires(await readFile(page, 'utf8'));
    /* Seuls les blocs SANS `type`, ou portant un type JavaScript, sont
       évalués : un <script type="application/json"> est un porteur de
       données inerte (voir rbi-tuilage.html) et n'est pas du code. Il
       est contrôlé séparément, en tant que JSON. */
    const blocs = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)]
      .filter(([, attrs]) => !/\bsrc=/.test(attrs))
      .filter(([, attrs]) => {
        const type = (attrs.match(/type="([^"]+)"/) || [])[1];
        return !type || /^(text\/javascript|module|text\/babel)$/.test(type);
      });
    for (const [i, m] of blocs.entries()) {
      try { new Function(m[2]); ok(true, `${path.relative(ROOT, page)} — script inline #${i + 1}`); }
      catch (e) { ok(false, `${path.relative(ROOT, page)} — script inline #${i + 1}`, e.message); }
    }

    for (const m of html.matchAll(/<script[^>]*type="application\/json"[^>]*>([\s\S]*?)<\/script>/gi)) {
      try { JSON.parse(m[1]); ok(true, `${path.relative(ROOT, page)} — bloc de données JSON`); }
      catch (e) { ok(false, `${path.relative(ROOT, page)} — bloc de données JSON`, e.message); }
    }
  }
}

/* ── 2. JSON-LD ─────────────────────────────────────────────── */
async function testJsonLd() {
  section('JSON-LD (référencement)');
  const pages = await listerFichiers(ROOT, n => n.endsWith('.html'), new Set(['.git', 'node_modules', 'dist', 'backup']));
  let trouves = 0;
  for (const page of pages) {
    const html = sansCommentaires(await readFile(page, 'utf8'));
    for (const [i, m] of [...html.matchAll(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)].entries()) {
      trouves++;
      try { JSON.parse(m[1]); ok(true, `${path.relative(ROOT, page)} — bloc #${i + 1}`); }
      catch (e) { ok(false, `${path.relative(ROOT, page)} — bloc #${i + 1}`, e.message); }
    }
  }
  ok(trouves > 0, 'au moins un bloc JSON-LD présent sur le site');
}

/* ── 3. Contrat du pont Make.com ────────────────────────────── */
async function testPont() {
  section('Pont Make.com — contrat JSON strict');
  const bridge = require_(path.join(ROOT, 'tools', 'make-bridge.js'));
  const { dispatch, parseStrict, toStrictJson } = bridge;

  const enveloppeValide = r =>
    typeof r === 'object' && typeof r.ok === 'boolean' &&
    'action' in r && 'requestId' in r && r.meta && typeof r.meta.at === 'string' &&
    (r.ok ? 'data' in r : (r.error && typeof r.error.code === 'string'));

  const ping = dispatch({ action: 'ping', requestId: 'test-1' });
  ok(enveloppeValide(ping) && ping.ok === true, 'ping → enveloppe conforme');
  ok(ping.requestId === 'test-1', 'requestId renvoyé à l\'identique');

  /* La sortie doit survivre à un aller-retour JSON : c'est exactement
     ce que fera Make.com. Un test sur l'objet en mémoire ne prouverait
     rien sur ce qui transite réellement. */
  for (const action of ['ping', 'site.manifest', 'content.get']) {
    const r = dispatch({ action });
    let identique = false;
    try { identique = JSON.stringify(JSON.parse(toStrictJson(r))) === JSON.stringify(r); } catch { /* laissé faux */ }
    ok(identique, `${action} → sérialisable en JSON strict et stable`);
  }

  ok(dispatch({}).error?.code === 'E_MISSING_ACTION', 'action absente → E_MISSING_ACTION');
  ok(dispatch({ action: 'nope' }).error?.code === 'E_UNKNOWN_ACTION', 'action inconnue → E_UNKNOWN_ACTION');
  ok(dispatch({ action: 'ping', params: [] }).error?.code === 'E_BAD_PARAMS', 'params tableau → E_BAD_PARAMS');
  ok(dispatch({ action: 'content.get', params: { path: '__proto__' } }).error?.code === 'E_FORBIDDEN_PATH', 'chemin __proto__ refusé');
  ok(dispatch({ action: 'content.get', params: { path: 'chefs.membres.999' } }).error?.code === 'E_PATH_NOT_FOUND', 'chemin inexistant → E_PATH_NOT_FOUND');
  ok(dispatch({ action: 'content.get', params: { path: 'contact.email' } }).data?.value?.includes('@'), 'content.get lit bien la config');

  for (const [brut, code] of [['', 'E_EMPTY_BODY'], ['{oups}', 'E_INVALID_JSON'], ['[1,2]', 'E_NOT_AN_OBJECT']]) {
    let obtenu = null;
    try { parseStrict(brut); } catch (e) { obtenu = e.rbiCode; }
    ok(obtenu === code, `entrée ${JSON.stringify(brut)} → ${code}`);
  }
  ok(parseStrict('﻿{"action":"ping"}').action === 'ping', 'BOM UTF-8 toléré en tête de corps');

  /* Le verdict du serveur doit être identique à celui de la page :
     on rejoue les réponses de config.js à travers le pont. */
  const cfg = dispatch({ action: 'content.get', params: { path: 'tuilage.questions' } }).data.value;
  const bonnes = Object.fromEntries(cfg.map(q => [q.id, q.reponses[0]]));
  ok(dispatch({ action: 'tuilage.verify', params: { answers: bonnes } }).data.reconnu === true, 'tuilage : réponses de config.js acceptées');
  ok(dispatch({ action: 'tuilage.verify', params: { answers: { q1: 'profane', q2: 'profane' } } }).data.reconnu === false, 'tuilage : réponses fausses refusées');
  const accents = Object.fromEntries(cfg.map(q => [q.id, q.reponses[0].toUpperCase() + ' !!!']));
  ok(dispatch({ action: 'tuilage.verify', params: { answers: accents } }).data.reconnu === true, 'tuilage : casse et ponctuation neutralisées');
  ok(dispatch({ action: 'tuilage.verify', params: { answers: cfg.map(q => q.reponses[0]) } }).data.reconnu === true, 'tuilage : forme tableau acceptée');
  ok(dispatch({ action: 'tuilage.verify', params: { answers: {} } }).data.reconnu === false, 'tuilage : réponses vides refusées');

  const c = dispatch({ action: 'contact.normalize', params: { payload: { nom: ' Test ', email: 'A@B.FR', message: 'x' } } }).data;
  ok(c.valide === true && c.record.email === 'a@b.fr' && c.record.nom === 'Test', 'contact.normalize : normalisation');
  ok(dispatch({ action: 'contact.normalize', params: { payload: { email: 'pasunemail', message: '' } } }).data.valide === false, 'contact.normalize : refus d\'un payload invalide');

  /* Le schéma est le contrat publié : il doit rester du JSON valide
     et décrire exactement les actions réellement exposées. */
  const schema = JSON.parse(await readFile(path.join(ROOT, 'tools', 'make-bridge.schema.json'), 'utf8'));
  const declarees = schema.$defs.requete.properties.action.enum.slice().sort();
  const reelles = Object.keys(bridge.ACTIONS).sort();
  ok(JSON.stringify(declarees) === JSON.stringify(reelles), 'schéma ↔ actions implémentées', `${declarees} vs ${reelles}`);
}

/* ── 4. Cohérence config ↔ pages ────────────────────────────── */
async function testCoherence() {
  section('Cohérence config.js ↔ code');
  const bridge = require_(path.join(ROOT, 'tools', 'make-bridge.js'));
  const cfg = bridge.dispatch({ action: 'content.get' }).data;
  const images = await readFile(path.join(ROOT, 'assets', 'images.js'), 'utf8');
  const appjs  = await readFile(path.join(ROOT, 'assets', 'app.js'), 'utf8');

  /* Ces `id` sont le contrat entre les trois couches. Rien, à
     l'exécution, ne signale leur rupture : la section reste vide,
     sans erreur. D'où ce test — le seul endroit où l'oubli devient
     visible avant la mise en ligne. */
  /* Un média non injecté n'est PAS une panne : la carte affiche alors
     son placeholder, comportement prévu par la maquette (voir app.js
     §4). C'est en revanche une omission éditoriale qu'il faut voir —
     d'où l'avertissement. */
  for (const m of cfg.chefs.membres) {
    if (images.includes(`'${m.img_id}'`)) ok(true, `images.js injecte « ${m.img_id} »`);
    else avertir(`aucune photo injectée pour « ${m.nom} » (${m.img_id}) → placeholder affiché`);
  }
  for (const l of cfg.livres.liste) {
    if (images.includes(`'${l.img_id}'`)) ok(true, `images.js injecte « ${l.img_id} »`);
    else avertir(`aucune couverture injectée pour « ${l.titre} » (${l.img_id})`);
  }
  ok(cfg.tuilage.pdfs.length === 3, 'tuilage : 3 documents déclarés (images.js en câble exactement 3)');
  ok(/tuilage-input-/.test(appjs) && /tuilage-btn-/.test(appjs), 'app.js construit bien les champs de tuilage');
  ok(cfg.tuilage.questions.every(q => Array.isArray(q.reponses) && q.reponses.length > 0), 'chaque question a au moins une réponse acceptée');
  ok(cfg.tuilage.max_essais >= 1, 'max_essais exploitable');

  const index = await readFile(path.join(ROOT, 'index.html'), 'utf8');
  const ordre = ['assets/config.js', 'assets/app.js', 'assets/images.js'].map(s => index.indexOf(s));
  ok(ordre.every(i => i !== -1) && ordre[0] < ordre[1] && ordre[1] < ordre[2], 'index.html : ordre config → app → images respecté');
}

console.log('═══ RBI — tests statiques et unitaires ═══');
await testSyntaxe();
await testJsonLd();
await testPont();
await testCoherence();

console.log(`\n${passes} réussis, ${echecs.length} échoués, ${avertissements.length} avertissements`);
if (avertissements.length) {
  console.log('\nAvertissements (non bloquants) :');
  for (const a of avertissements) console.log('  ! ' + a.titre + (a.detail ? ' — ' + a.detail : ''));
}
/* Le code de sortie est le seul signal que lit la CI : il ne doit
   dépendre QUE des échecs réels. */
if (echecs.length) { console.log('\nÉchecs :\n' + JSON.stringify(echecs, null, 2)); process.exit(1); }
