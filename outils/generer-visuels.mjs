#!/usr/bin/env node
/* ═══════════════════════════════════════════════════════════════
   Génération des visuels de promotion.

     node outils/generer-visuels.mjs

   Produit les images dans assets/social/. Le contenu se modifie dans
   outils/visuels/cartes.mjs, l'apparence dans visuels/gabarits.mjs.

   Les couvertures ne sont pas dupliquées : elles sont relues à chaque
   exécution depuis assets/images.js, qui reste la seule source. Une
   couverture remplacée là se propage à tous les visuels sans qu'on ait
   à y penser.
════════════════════════════════════════════════════════════════ */

import { chromium } from 'playwright';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { FORMATS, LIVRES, CARTES } from './visuels/cartes.mjs';
import { GABARITS } from './visuels/gabarits.mjs';

const RACINE = join(dirname(fileURLToPath(import.meta.url)), '..');
const SORTIE = join(RACINE, 'assets', 'social');

/* Les images du site sont stockées en base64 dans un fichier
   JavaScript. On y lit directement la valeur voulue plutôt que
   d'évaluer le fichier : il pèse plus d'un mégaoctet, et l'évaluer
   pour trois chaînes serait payer cher une commodité. */
function couverture(cle) {
  const src = readFileSync(join(RACINE, 'assets', 'images.js'), 'utf8');
  const m = src.match(new RegExp(`${cle}\\s*:\\s*"(data:image/[a-z]+;base64,[A-Za-z0-9+/=]+)"`));
  if (!m) throw new Error(`Couverture introuvable dans assets/images.js : ${cle}`);
  return m[1];
}

function html(carte, format) {
  const { l, h } = FORMATS[format];
  const gabarit = GABARITS[carte.type];
  if (!gabarit) throw new Error(`Type de carte inconnu : ${carte.type}`);
  if (carte.type !== 'livre') return gabarit(carte, l, h);
  const livre = LIVRES[carte.livre];
  if (!livre) throw new Error(`Livre inconnu : ${carte.livre}`);
  return gabarit({ ...livre, couverture: couverture(livre.cle) }, l, h);
}

async function main() {
  mkdirSync(SORTIE, { recursive: true });
  const navigateur = await chromium.launch();
  const produits = [];

  try {
    for (const carte of CARTES) {
      for (const format of carte.formats) {
        const { l, h } = FORMATS[format];
        const page = await navigateur.newPage({ viewport: { width: l, height: h } });
        await page.setContent(html(carte, format), { waitUntil: 'load' });
        /* Les couvertures sont en data:URI — décodées, pas téléchargées —
           mais le décodage n'est pas instantané pour 50 Ko de JPEG. */
        await page.waitForFunction(
          () => Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)
        );
        const nom = `${carte.id}-${format}.png`;
        await page.screenshot({ path: join(SORTIE, nom) });
        await page.close();
        produits.push(nom);
        console.log(`  ✓ ${nom}  (${l}×${h})`);
      }
    }
  } finally {
    await navigateur.close();
  }

  /* Un index lisible, pour retrouver un visuel sans ouvrir le dossier. */
  writeFileSync(join(SORTIE, 'INDEX.txt'),
    `Visuels de promotion — Rite Brith Israël\n` +
    `Régénérer : node outils/generer-visuels.mjs\n` +
    `Ne pas retoucher à la main : toute modification est écrasée.\n\n` +
    produits.map(n => '  ' + n).join('\n') + '\n');

  console.log(`\n${produits.length} visuels dans assets/social/`);
}

main().catch(e => { console.error('Échec :', e.message); process.exit(1); });
