/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — tools/test-components.mjs
   Tests des composants réutilisables (components/).

   ── CE QUE CES COMPOSANTS PROMETTENT ─────────────────────────
   Ils sont destinés à être collés dans des pages INCONNUES (Canva,
   CMS, newsletter, site partenaire). Leur promesse n'est donc pas
   seulement « ça s'affiche », c'est « ça ne casse rien chez l'hôte ».
   Cette promesse n'est vérifiable que par une analyse du CSS lui-même :
   un rendu visuel correct dans une page vide ne prouve rien.

   D'où les contrôles ci-dessous, qui sont la traduction mécanique des
   règles d'isolation documentées dans chaque composant :
     • aucun sélecteur qui échappe à la racine du composant ;
     • aucune variable posée sur :root (elle fuirait vers l'hôte) ;
     • aucune ressource distante (police, script, image) ;
     • target="_blank" toujours accompagné de rel="noopener".

   Le JSX est compilé puis RENDU côté serveur : une erreur de hook ou
   de prop se voit immédiatement, sans navigateur.
════════════════════════════════════════════════════════════════ */
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HTML_DIR = path.join(ROOT, 'components', 'html');

let passes = 0;
const echecs = [];
function ok(cond, titre, detail) {
  if (cond) { passes++; console.log('  ✓ ' + titre); }
  else { echecs.push({ titre, detail: detail ?? '' }); console.log('  ✗ ' + titre + (detail ? ' — ' + detail : '')); }
}
function section(t) { console.log('\n▸ ' + t); }

/* ── 1. Composants HTML autonomes ───────────────────────────── */
section('Composants HTML — isolation');
const fichiers = (await readdir(HTML_DIR)).filter(f => f.endsWith('.html')).sort();
ok(fichiers.length > 0, `${fichiers.length} composants trouvés`);

for (const f of fichiers) {
  const brut = await readFile(path.join(HTML_DIR, f), 'utf8');
  const nom = 'components/html/' + f;

  /* Les commentaires sont retirés AVANT toute analyse. Ces composants
     sont abondamment commentés, et un commentaire cite forcément le
     code qu'il explique : sans ce nettoyage, les analyses ci-dessous
     inspecteraient de la prose et signaleraient des problèmes
     imaginaires (un « <script type="application/json"> » évoqué dans
     une phrase, un sélecteur nommé dans une explication). */
  const src = brut.replace(/<!--[\s\S]*?-->/g, '');

  const racine = src.match(/class="(rbi-[a-z-]+)"[^>]*data-rbi-component/);
  ok(!!racine, `${nom} — racine identifiée par data-rbi-component`);
  const classeRacine = racine ? racine[1] : null;

  /* Idem pour les commentaires CSS, retirés avant l'extraction des
     sélecteurs : « /* ... *\/ » précède presque chaque règle ici. */
  const styles = [...src.matchAll(/<style>([\s\S]*?)<\/style>/g)].map(m => m[1]).join('\n')
    .replace(/\/\*[\s\S]*?\*\//g, '');
  ok(styles.length > 0, `${nom} — styles embarqués`);

  /* Chaque sélecteur doit être ancré sur la classe racine. Les at-rules
     (@media, @keyframes, @container, @supports) et les sélecteurs de
     keyframes (from/to/%) sont exclus : ils ne ciblent aucun élément
     de l'hôte. */
  const sansAtRules = styles.replace(/@(media|supports|container)[^{]*\{/g, '').replace(/@keyframes[^{]*\{[\s\S]*?\n\s*\}/g, '');
  const selecteurs = [...sansAtRules.matchAll(/(^|\})\s*([^{}@]+?)\s*\{/g)]
    .map(m => m[2].trim())
    .filter(s => s && !/^(from|to|\d+%)$/.test(s));
  const fuites = selecteurs.filter(s => !s.split(',').every(part => part.trim().startsWith('.' + classeRacine)));
  ok(fuites.length === 0, `${nom} — tous les sélecteurs ancrés sur .${classeRacine}`, fuites.slice(0, 3).join(' | '));

  /* Une variable posée sur :root déborderait sur toute la page hôte —
     c'est la fuite la plus fréquente et la plus difficile à diagnostiquer
     pour celui qui intègre le composant. */
  ok(!/:root\s*\{/.test(styles), `${nom} — aucune variable sur :root`);

  /* Aucune ressource distante : dans un embed, une requête tierce est
     souvent bloquée, et elle expose le visiteur de l'hôte à un service
     qu'il n'a pas choisi. */
  const distantes = [...src.matchAll(/(?:href|src)="(https?:\/\/[^"]+)"/g)]
    .map(m => m[1])
    .filter(u => !/^https?:\/\/(www\.)?(brith-israel\.org|coollibri\.com|amzn\.eu|facebook\.com)/.test(u));
  ok(distantes.length === 0, `${nom} — aucune ressource distante chargée`, distantes.slice(0, 2).join(' | '));
  ok(!/@import|fonts\.googleapis|fonts\.gstatic/.test(src), `${nom} — aucune police distante`);

  /* Un target="_blank" sans rel="noopener" donne à la page ouverte un
     accès à window.opener : le composant ferait courir ce risque à
     l'hôte, sans qu'il en sache rien. */
  const blancs = [...src.matchAll(/<a\b[^>]*target="_blank"[^>]*>/g)].map(m => m[0]);
  ok(blancs.every(a => /rel="[^"]*noopener/.test(a)), `${nom} — target="_blank" toujours avec rel="noopener"`,
     blancs.filter(a => !/noopener/.test(a)).slice(0, 1).join(''));

  /* Le JS embarqué doit être syntaxiquement valide et ne rien poser
     sur window : deux instances du composant, ou une page hôte
     utilisant le même nom, entreraient en collision. */
  for (const [i, m] of [...src.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)].entries()) {
    try { new Function(m[1]); ok(true, `${nom} — script #${i + 1} valide`); }
    catch (e) { ok(false, `${nom} — script #${i + 1} valide`, e.message); }
    ok(!/\bwindow\.[A-Za-z_$][\w$]*\s*=/.test(m[1]), `${nom} — script #${i + 1} n'écrit pas sur window`);
  }

  /* Les données déclaratives doivent rester du JSON valide : c'est le
     seul endroit qu'un intégrateur non développeur va modifier. */
  for (const m of src.matchAll(/<script type="application\/json"[^>]*>([\s\S]*?)<\/script>/g)) {
    try { JSON.parse(m[1]); ok(true, `${nom} — bloc de données JSON valide`); }
    catch (e) { ok(false, `${nom} — bloc de données JSON valide`, e.message); }
  }
}

/* ── 2. Composants React ────────────────────────────────────── */
section('Composants React — compilation et rendu');
let babel, React, renderToStaticMarkup;
try {
  babel = await import('@babel/core');
  React = (await import('react')).default;
  renderToStaticMarkup = (await import('react-dom/server')).renderToStaticMarkup;
} catch {
  console.log('  ! react/@babel absents → section sautée (npm ci pour les installer)');
}

if (babel) {
  const jsxPath = path.join(ROOT, 'components', 'react', 'rbi-components.jsx');
  const source = await readFile(jsxPath, 'utf8');

  /* Compilation en CommonJS : le module transformé est ensuite évalué
     dans ce processus. Passer par un import ESM natif obligerait à
     écrire le résultat sur disque — inutile, et cela laisserait un
     artefact non versionné traîner dans le dépôt. */
  let code;
  try {
    code = babel.transformSync(source, {
      filename: jsxPath,
      presets: [[(await import('@babel/preset-react')).default, { runtime: 'classic' }]],
      plugins: [],
      sourceType: 'module',
      configFile: false, babelrc: false
    }).code;
    ok(true, 'rbi-components.jsx — JSX compilé sans erreur');
  } catch (e) {
    ok(false, 'rbi-components.jsx — JSX compilé sans erreur', e.message.split('\n')[0]);
  }

  if (code) {
    /* Transformation ESM → CommonJS faite à la main, sur les seules
       formes utilisées par le fichier : ajouter @babel/plugin-transform-modules-commonjs
       pour deux lignes d'import serait une dépendance de plus à
       maintenir pour un gain nul. */
    const cjs = code
      .replace(/^import\s+React,\s*\{([^}]+)\}\s+from\s+'react';?$/m,
               "const React = require('react'); const {$1} = React;")
      .replace(/^export\s+(function|const)\s+/gm, '$1 ')
      .replace(/^export\s+default\s+[\s\S]*?;$/m, '');

    const module_ = { exports: {} };
    const composants = {};
    try {
      const fn = new Function('require', 'module', 'exports', cjs + '\nreturn { RbiHero, RbiChefCard, RbiBookCard, RbiTuilage, normaliseReponse, QUESTIONS_PAR_DEFAUT };');
      Object.assign(composants, fn((await import('node:module')).createRequire(jsxPath), module_, module_.exports));
      ok(true, 'rbi-components.jsx — module évaluable');
    } catch (e) {
      ok(false, 'rbi-components.jsx — module évaluable', e.message.split('\n')[0]);
    }

    /* Rendu statique : prouve que chaque composant s'exécute (hooks
       inclus) et produit du balisage. `useEffect` n'est pas joué au
       rendu serveur — c'est précisément pourquoi l'injection de style
       y est protégée par une garde `typeof document`. */
    for (const [nom, C] of Object.entries(composants)) {
      if (typeof C !== 'function' || !/^Rbi/.test(nom)) continue;
      try {
        const html = renderToStaticMarkup(React.createElement(C, {}));
        ok(html.includes('rbi-c'), `${nom} — rendu statique produit du balisage isolé`);
        ok(!html.includes('undefined'), `${nom} — aucune prop « undefined » rendue`);
      } catch (e) {
        ok(false, `${nom} — rendu statique`, e.message.split('\n')[0]);
      }
    }

    /* La normalisation doit rester STRICTEMENT identique aux deux
       autres implémentations (app.js et make-bridge.js). Trois copies
       existent pour des raisons documentées ; ce test est ce qui les
       empêche de diverger silencieusement. */
    if (composants.normaliseReponse) {
      const pont = (await import('node:module')).createRequire(import.meta.url)(path.join(ROOT, 'tools', 'make-bridge.js'));
      const cas = ['De Saint-Jean', 'ÉLÈVE  ', '7 ANS !!!', 'Trois, cinq et sept', ''];
      const identiques = cas.every(c => composants.normaliseReponse(c) === pont.normalise(c));
      ok(identiques, 'normalisation React ↔ pont Make.com : résultats identiques',
         cas.map(c => `${JSON.stringify(c)} → ${composants.normaliseReponse(c)} / ${pont.normalise(c)}`).join(' | '));
    }
  }
}

/* ── 3. Page de démonstration ───────────────────────────────── */
section('Page de démonstration');
const demo = await readFile(path.join(ROOT, 'components', 'demo.html'), 'utf8');
for (const f of fichiers) ok(demo.includes('html/' + f), `demo.html référence ${f}`);
ok(/react\/rbi-components\.jsx/.test(demo), 'demo.html importe le vrai fichier de composants (pas une copie)');
/* Les versions du CDN doivent être épinglées : une URL en « @latest »
   ferait dépendre le rendu de la démonstration du jour où on l'ouvre. */
const cdn = [...demo.matchAll(/https:\/\/cdnjs\.cloudflare\.com\/[^"]+/g)].map(m => m[0]);
ok(cdn.length > 0 && cdn.every(u => /\/\d+\.\d+\.\d+\//.test(u)), 'demo.html — versions CDN épinglées', cdn.join(' | '));

console.log(`\n${passes} réussis, ${echecs.length} échoués`);
if (echecs.length) { console.log(JSON.stringify(echecs, null, 2)); process.exit(1); }
