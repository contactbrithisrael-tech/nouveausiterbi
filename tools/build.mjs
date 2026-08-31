/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — tools/build.mjs
   Produit `dist/`, la copie déployable du site.

   ── PRINCIPE : LE BUILD EST OPTIONNEL ────────────────────────
   Le dépôt reste directement servable tel quel (voir assets/app.js).
   Ce script ne fait que RÉDUIRE le poids d'une copie ; il ne
   transpile rien, ne réécrit aucun chemin, ne change aucune
   arborescence. Conséquence recherchée : `dist/` et la racine sont
   interchangeables, et un déploiement peut se replier sur les
   sources si la chaîne de build casse.

   ── SEUIL DE MINIFICATION ────────────────────────────────────
   Les fichiers volumineux du dépôt sont volumineux à cause de leurs
   data-URI base64, incompressibles par un minifieur : les passer à
   terser/html-minifier coûte des minutes de CPU pour un gain proche
   de zéro, et fait échouer le build par dépassement mémoire sur les
   plus gros (traites.html ≈ 17 Mo). Au-delà de MAX_MINIFY, on copie
   donc à l'identique — décision de coût, pas de facilité.

   ── IDEMPOTENCE ──────────────────────────────────────────────
   `dist/` est effacé à chaque exécution : un artefact laissé par un
   build précédent (fichier supprimé depuis) serait sinon déployé
   indéfiniment. Le manifeste écrit en fin de course sert de preuve
   de contenu pour l'étape de déploiement.
════════════════════════════════════════════════════════════════ */
import { readFile, writeFile, mkdir, rm, readdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(ROOT, 'dist');

/* Exclusions : rien qui ne soit servi au visiteur. `backup/` est une
   archive de travail — la déployer publierait d'anciennes versions du
   site sous une URL devinable. */
/* `components/` EST déployé, contrairement à `tools/` : les composants
   isolés n'ont d'utilité que servis par une URL publique — c'est ce qui
   permet de les intégrer en iframe dans Canva, un CMS ou un site
   partenaire. `tools/`, `.github/` et `backup/` restent exclus : ce sont
   respectivement de l'outillage, de la configuration CI et une archive,
   dont la publication n'apporterait rien et exposerait d'anciennes
   versions du site. */
const EXCLUS = new Set(['.git', 'node_modules', 'dist', 'backup', 'tools', '.github', '.claude']);
const EXCLUS_FICHIERS = new Set(['structure.txt', 'package.json', 'package-lock.json', '.gitignore']);

const MAX_MINIFY = 1_500_000;  // octets — au-delà : copie verbatim

const stats = { minifies: 0, copies: 0, octetsAvant: 0, octetsApres: 0, fichiers: [] };

/* Chargement paresseux des minifieurs : ce sont des devDependencies.
   Si elles manquent (installation partielle, exécution hors CI), le
   build se poursuit en mode copie au lieu d'échouer — le site produit
   reste correct, seulement plus lourd. */
async function chargerMinifieurs() {
  const out = { js: null, css: null, html: null };
  try { out.js   = (await import('terser')).minify; }                     catch { console.error('[build] terser absent → JS copié tel quel'); }
  try { out.css  = new (await import('clean-css')).default({ level: 2 }); } catch { console.error('[build] clean-css absent → CSS copié tel quel'); }
  try { out.html = (await import('html-minifier-terser')).minify; }        catch { console.error('[build] html-minifier-terser absent → HTML copié tel quel'); }
  return out;
}

async function lister(dir, base = '') {
  const entrees = await readdir(dir, { withFileTypes: true });
  const fichiers = [];
  for (const e of entrees) {
    const rel = path.posix.join(base, e.name);
    if (e.isDirectory()) {
      if (EXCLUS.has(e.name)) continue;
      fichiers.push(...await lister(path.join(dir, e.name), rel));
    } else {
      if (EXCLUS_FICHIERS.has(e.name)) continue;
      fichiers.push(rel);
    }
  }
  return fichiers;
}

async function main() {
  const min = await chargerMinifieurs();
  await rm(DIST, { recursive: true, force: true });
  await mkdir(DIST, { recursive: true });

  const fichiers = await lister(ROOT);

  for (const rel of fichiers) {
    const src = path.join(ROOT, rel);
    const dst = path.join(DIST, rel);
    await mkdir(path.dirname(dst), { recursive: true });

    const taille = (await stat(src)).size;
    const ext = path.extname(rel).toLowerCase();
    const minifiable = taille <= MAX_MINIFY && ['.js', '.css', '.html'].includes(ext);

    if (!minifiable) {
      /* Copie binaire : les PDF et les gros HTML passent par un Buffer
         brut, jamais par une chaîne — un décodage UTF-8 corromprait
         les octets d'un PDF. */
      const buf = await readFile(src);
      await writeFile(dst, buf);
      stats.copies++; stats.octetsAvant += taille; stats.octetsApres += taille;
      stats.fichiers.push({ fichier: rel, action: 'copie', avant: taille, apres: taille });
      continue;
    }

    const source = await readFile(src, 'utf8');
    let sortie = source;
    try {
      if (ext === '.js' && min.js) {
        /* `compress`/`mangle` conservateurs : le site n'a pas de tests
           unitaires exhaustifs sur son JS, et une transformation
           agressive (drop_console, unsafe) échangerait quelques
           kilo-octets contre un risque de régression silencieuse en
           production. Le rapport n'est pas favorable ici. */
        const r = await min.js(source, {
          ecma: 5,
          compress: { defaults: true, drop_console: false, passes: 1 },
          mangle: true,
          format: { comments: false }
        });
        if (r.code) sortie = r.code;
      } else if (ext === '.css' && min.css) {
        const r = min.css.minify(source);
        if (r.errors?.length) throw new Error(r.errors.join('; '));
        sortie = r.styles;
      } else if (ext === '.html' && min.html) {
        sortie = await min.html(source, {
          collapseWhitespace: true,
          removeComments: true,
          minifyCSS: true,
          minifyJS: true,
          /* Attributs et guillemets préservés : les scripts inline et
             app.js retrouvent leurs cibles par `id` et par `class` ;
             les optimisations qui touchent aux attributs feraient
             porter au build un risque sur ce contrat. */
          removeAttributeQuotes: false,
          removeEmptyAttributes: false,
          keepClosingSlash: true
        });
      }
    } catch (e) {
      /* Un échec de minification ne doit jamais casser un déploiement :
         on retombe sur la source, en le signalant fort. */
      console.error(`[build] minification impossible (${rel}) : ${e.message} → copie verbatim`);
      sortie = source;
    }

    await writeFile(dst, sortie, 'utf8');
    const apres = Buffer.byteLength(sortie, 'utf8');
    stats.minifies++; stats.octetsAvant += taille; stats.octetsApres += apres;
    stats.fichiers.push({ fichier: rel, action: 'minifie', avant: taille, apres });
  }

  /* Manifeste : JSON strict, consommable par l'étape de déploiement
     comme par un scénario Make.com de supervision. L'empreinte permet
     de vérifier après transfert que le serveur a bien reçu ce build. */
  const empreinte = createHash('sha256')
    .update(stats.fichiers.map(f => `${f.fichier}:${f.apres}`).join('\n'))
    .digest('hex');

  const manifeste = {
    ok: true,
    genereLe: new Date().toISOString(),
    fichiers: stats.fichiers.length,
    minifies: stats.minifies,
    copies: stats.copies,
    octetsAvant: stats.octetsAvant,
    octetsApres: stats.octetsApres,
    gainPourcent: stats.octetsAvant ? +(100 * (1 - stats.octetsApres / stats.octetsAvant)).toFixed(2) : 0,
    empreinte,
    detail: stats.fichiers
  };
  await writeFile(path.join(DIST, 'build-manifest.json'), JSON.stringify(manifeste, null, 2), 'utf8');

  console.error(`[build] ${manifeste.fichiers} fichiers — ${manifeste.minifies} minifiés, ${manifeste.copies} copiés`);
  console.error(`[build] ${(manifeste.octetsAvant / 1e6).toFixed(2)} Mo → ${(manifeste.octetsApres / 1e6).toFixed(2)} Mo (${manifeste.gainPourcent} %)`);
  /* Le manifeste part sur stdout : `node tools/build.mjs > build.json`
     reste du JSON strict, exploitable par Make.com. */
  process.stdout.write(JSON.stringify(manifeste) + '\n');
}

main().catch(e => { console.error('[build] ÉCHEC : ' + e.stack); process.exit(1); });
