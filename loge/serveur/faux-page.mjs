/* ═══════════════════════════════════════════════════════════════════
   LA PAGE D'ÉPREUVE

   L'épreuve de la porte doit taper un mot de passe. Écrire les vrais
   dans le dépôt reviendrait à les publier : Cloudflare Pages sert tout
   ce qu'il porte.

   On sert donc une COPIE de la page où les deux empreintes de la porte
   sont remplacées par celles de mots de passe inventés. Le code éprouvé
   est le même à la ligne près ; seules les serrures changent.

   Usage :  node loge/serveur/faux-page.mjs > /tmp/page-epreuve.html
═══════════════════════════════════════════════════════════════════ */
import fs from 'node:fs';

const RACINE = new URL('../../', import.meta.url).pathname;

/* Les mêmes que dans faux-serveur.mjs : l'épreuve du repli vérifie
   justement qu'un mot de passe accepté par la page ouvre encore quand
   le serveur, lui, refuse. */
export const CLES = { secretariat: 'cleSecretariatEpreuve',
                      tresorerie:  'cleTresorerieEpreuve' };

const sha256 = async t => [...new Uint8Array(await crypto.subtle.digest(
  'SHA-256', new TextEncoder().encode(t)))]
  .map(o => o.toString(16).padStart(2, '0')).join('');

let page = fs.readFileSync(RACINE + 'secretariat.html', 'utf8');

for (const [role, mdp] of Object.entries(CLES)){
  const bloc = new RegExp(`(${role}:\\s*\\{\\s*\\n\\s*empreinte:\\s*')[a-f0-9]{64}(')`);
  if (!bloc.test(page)){
    console.error(`empreinte de « ${role} » introuvable : la porte a changé de forme`);
    process.exit(1);
  }
  page = page.replace(bloc, `$1${await sha256(mdp.toLowerCase())}$2`);
}

process.stdout.write(page);
