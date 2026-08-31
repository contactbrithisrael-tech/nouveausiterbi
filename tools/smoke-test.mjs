/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — tools/smoke-test.mjs
   Parcours réel dans un navigateur sans interface.

   ── CE QUE CE TEST PROUVE, ET LUI SEUL ───────────────────────
   Le site n'a AUCUN rendu serveur : sa page n'existe qu'une fois
   config.js lu et app.js exécuté. Aucune analyse statique ne peut
   donc dire si la page finale est correcte. Ce test est la seule
   vérification qui exerce la chaîne complète — ordre des scripts,
   construction du DOM, injection des médias, parcours de tuilage —
   dans le moteur qui la subira en production.

   ── IL S'EXÉCUTE SUR `dist/` PAR DÉFAUT ──────────────────────
   C'est l'artefact qui sera déployé, pas les sources : la
   minification est précisément l'étape qui peut casser un site sans
   qu'aucun test de source ne le voie. Passer un chemin en argument
   permet de tester la racine (`node tools/smoke-test.mjs .`).

   ── SERVEUR STATIQUE INTERNE ─────────────────────────────────
   Les pages sont chargées en http:// et non en file:// : ce dernier
   applique une politique d'origine différente et donnerait un verdict
   qui ne correspond à aucune situation réelle.
════════════════════════════════════════════════════════════════ */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CIBLE = path.resolve(ROOT, process.argv[2] || 'dist');
const PORT = Number(process.env.RBI_SMOKE_PORT || 8123);
/* Le pont Make.com est aussi le lecteur de référence de config.js :
   le réutiliser ici évite une seconde implémentation de lecture — et
   donc un second endroit où la configuration pourrait être mal lue. */
const pont = createRequire(import.meta.url)(path.join(ROOT, 'tools', 'make-bridge.js'));

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
                '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.pdf': 'application/pdf',
                '.png': 'image/png', '.jpg': 'image/jpeg', '.zip': 'application/zip', '.txt': 'text/plain; charset=utf-8' };

let passes = 0;
const echecs = [];
function ok(cond, titre, detail) {
  if (cond) { passes++; console.log('  ✓ ' + titre); }
  else { echecs.push({ titre, detail: detail ?? '' }); console.log('  ✗ ' + titre + (detail ? ' — ' + detail : '')); }
}

function servir() {
  return new Promise(resolve => {
    const s = http.createServer((req, res) => {
      const rel = decodeURIComponent((req.url || '/').split('?')[0]).replace(/^\/+/, '') || 'index.html';
      /* Confinement du serveur de test à son dossier : une requête
         « ../../etc/passwd » doit échouer même ici, sans quoi le test
         validerait des chemins qu'un vrai serveur refuserait. */
      const cible = path.resolve(CIBLE, rel);
      if (!cible.startsWith(CIBLE)) { res.writeHead(403).end(); return; }
      fs.readFile(cible, (err, buf) => {
        if (err) { res.writeHead(404).end('404'); return; }
        res.writeHead(200, { 'content-type': TYPES[path.extname(cible).toLowerCase()] || 'application/octet-stream' });
        res.end(buf);
      });
    });
    s.listen(PORT, () => resolve(s));
  });
}

async function chargerChromium() {
  /* playwright-core d'abord : il n'embarque aucun navigateur et suffit
     quand l'environnement en fournit déjà un (conteneur CI, image de
     base). playwright ensuite, pour un poste où il a téléchargé le
     sien. Sans aucun des deux, on SAUTE le test au lieu d'échouer :
     un poste sans navigateur ne doit pas bloquer un commit — la CI,
     elle, en a toujours un (voir .github/workflows/ci.yml). */
  for (const paquet of ['playwright-core', 'playwright']) {
    try { return (await import(paquet)).chromium; } catch { /* essai suivant */ }
  }
  return null;
}

const chromium = await chargerChromium();
if (!chromium) {
  console.log('[smoke] playwright absent → test sauté (voir devDependencies)');
  process.exit(0);
}
if (!fs.existsSync(path.join(CIBLE, 'index.html'))) {
  console.error(`[smoke] ${path.relative(ROOT, CIBLE)}/index.html introuvable — lancer d'abord « npm run build »`);
  process.exit(1);
}

console.log(`═══ RBI — test de fumée sur ${path.relative(ROOT, CIBLE) || '.'} ═══`);
const serveur = await servir();
const navigateur = await chromium.launch(process.env.RBI_CHROMIUM ? { executablePath: process.env.RBI_CHROMIUM } : {});
const page = await navigateur.newPage();

const erreursPage = [];
page.on('pageerror', e => erreursPage.push('pageerror: ' + e.message));
/* Un message de console ne dit pas QUELLE ressource a échoué : on
   suit donc les réponses HTTP en parallèle, pour que l'échec du test
   nomme l'URL fautive au lieu d'un « 404 » anonyme à rechercher à la
   main. La requête /favicon.ico est émise par le navigateur lui-même,
   pas par le site : elle est exclue du verdict (son absence relève de
   l'habillage, pas d'une régression de code). */
page.on('console', m => {
  /* Le texte d'un message de console d'erreur réseau ne contient PAS
     l'URL (« Failed to load resource... ») : elle n'est disponible que
     dans location(). Filtrer sur le texte seul laisserait donc passer
     le favicon et rendrait le test rouge en permanence. */
  const url = (m.location() || {}).url || '';
  if (m.type() === 'error' && !/favicon\.ico/i.test(url)) erreursPage.push('console: ' + m.text() + (url ? ' [' + url + ']' : ''));
});
page.on('response', r => {
  if (r.status() >= 400 && !/favicon\.ico$/i.test(r.url())) erreursPage.push(`http ${r.status()}: ${r.url()}`);
});

try {
  /* `load` et non `domcontentloaded` : images.js injecte les médias sur
     `load`. Attendre moins reviendrait à photographier la page avant
     l'étape que l'on veut justement vérifier. */
  await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'load' });

  const vue = await page.evaluate(() => ({
    liens:    document.querySelectorAll('#nav-links a').length,
    titre:    (document.getElementById('hero-title') || {}).textContent || '',
    cartes:   document.querySelectorAll('#rite-cards .card').length,
    chefs:    document.querySelectorAll('#chefs-grid .chef-card').length,
    livres:   document.querySelectorAll('#books-grid .book-card').length,
    etapes:   document.querySelectorAll('#tuilage-zone .tuilage__step').length,
    contact:  document.querySelectorAll('#contact-block a').length,
    pied:     document.querySelectorAll('#footer-content p').length,
    etoiles:  document.querySelectorAll('#stars-container .star').length,
    sceau:    !!(document.getElementById('hero-seal') || {}).src
  }));

  /* Les valeurs attendues viennent de config.js — relue ici par le
     pont, qui en est déjà le lecteur officiel — et jamais de constantes
     recopiées : ajouter un dignitaire ou une question ne doit pas faire
     échouer la CI. Le test vérifie la COHÉRENCE page ↔ configuration,
     pas des nombres figés. */
  const contenu = pont.dispatch({ action: 'content.get' }).data;

  ok(vue.liens === contenu.navbar.liens.length, `navbar : ${vue.liens} liens`);
  ok(vue.titre.includes(contenu.hero.titre_fr), 'hero : titre injecté depuis config.js');
  ok(vue.cartes === contenu.rite.cartes.length, `rite : ${vue.cartes} cartes`);
  ok(vue.chefs === contenu.chefs.membres.length, `chefs : ${vue.chefs} cartes`);
  ok(vue.livres === contenu.livres.liste.length, `livres : ${vue.livres} fiches`);
  ok(vue.etapes === contenu.tuilage.questions.length + 3, `tuilage : ${vue.etapes} étapes (départ + questions + succès + échec)`);
  ok(vue.contact >= 3, 'contact : liens présents');
  ok(vue.pied === 3, 'pied de page : 3 lignes');
  ok(vue.etoiles === 120, 'hero : 120 étoiles générées');
  ok(vue.sceau, 'images.js : sceau injecté');

  /* Parcours nominal complet, joué avec les réponses de config.js :
     c'est le seul chemin par lequel un visiteur atteint les documents. */
  await page.click('#tuilage-start-btn');
  for (const [i, q] of contenu.tuilage.questions.entries()) {
    await page.fill(`#tuilage-input-${i + 1}`, q.reponses[0]);
    await page.click(`#tuilage-btn-${i + 1}`);
    await page.waitForTimeout(1100);   // > 900 ms : délai de lecture d'app.js
  }
  ok(await page.evaluate(() => !document.getElementById('tuilage-success').classList.contains('tuilage__step--hidden')),
     'tuilage : parcours nominal → étape succès');

  /* Chemin d'échec : trois erreurs doivent mener à l'étape d'échec,
     puis « Recommencer » doit ramener un état propre. */
  await page.reload({ waitUntil: 'load' });
  await page.click('#tuilage-start-btn');
  for (let i = 0; i < contenu.tuilage.max_essais; i++) {
    await page.fill('#tuilage-input-1', 'profane ' + i);
    await page.click('#tuilage-btn-1');
  }
  ok(await page.evaluate(() => !document.getElementById('tuilage-fail').classList.contains('tuilage__step--hidden')),
     `tuilage : ${contenu.tuilage.max_essais} erreurs → étape échec`);
  await page.click('#tuilage-retry-btn');
  ok(await page.evaluate(() => !document.getElementById('tuilage-start').classList.contains('tuilage__step--hidden')
                            && document.getElementById('tuilage-input-1').value === ''),
     'tuilage : « Recommencer » réinitialise le parcours');

  await page.click('#chefs-grid .chef-card');
  ok(await page.evaluate(() => !!document.getElementById('chef-lightbox')), 'lightbox chef : ouverture');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  ok(await page.evaluate(() => !document.getElementById('chef-lightbox')), 'lightbox chef : fermeture par Échap');

  /* Contrôle anti-fuite : l'écouteur « Échap » de la lightbox doit se
     retirer lui-même (voir app.js). On ouvre et ferme plusieurs fois,
     puis on vérifie qu'une pression sur Échap sans lightbox ouverte ne
     déclenche aucune erreur. */
  for (let i = 0; i < 3; i++) {
    await page.click('#chefs-grid .chef-card');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(120);
  }
  await page.keyboard.press('Escape');
  ok(await page.evaluate(() => !document.getElementById('chef-lightbox')), 'lightbox : ouvertures répétées sans état résiduel');

  /* Le menu mobile verrouille le défilement du corps : un verrou resté
     actif rendrait la page inutilisable après fermeture. */
  await page.setViewportSize({ width: 390, height: 844 });
  await page.click('#burger-btn');
  ok(await page.evaluate(() => document.body.style.overflow === 'hidden'), 'burger : ouverture verrouille le défilement');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  ok(await page.evaluate(() => document.body.style.overflow === ''), 'burger : fermeture libère le défilement');

  /* Les erreurs réseau vers des services tiers (YouTube) ne sont pas du
     ressort du site : elles dépendent de la connectivité du runner. */
  const pertinentes = erreursPage.filter(e => !/youtube|iframe_api|ERR_(NAME|INTERNET|CONNECTION|BLOCKED)|net::/i.test(e));
  ok(pertinentes.length === 0, 'aucune erreur JavaScript ni ressource manquante', pertinentes.join(' | '));
} finally {
  await navigateur.close();
  serveur.close();
}

console.log(`\n${passes} réussis, ${echecs.length} échoués`);
if (echecs.length) { console.log(JSON.stringify(echecs, null, 2)); process.exit(1); }
