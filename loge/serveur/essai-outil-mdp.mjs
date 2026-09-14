/* ═══════════════════════════════════════════════════════════════════
   L'ÉPREUVE DE L'OUTIL À MOTS DE PASSE

   nouveau-mdp.mjs imprime du SQL à coller dans la console D1. Du SQL
   imprimé qui ne marche pas, on ne s'en aperçoit qu'au moment où
   quelqu'un a perdu son mot de passe et attend derrière la porte.

   On l'éprouve donc pour de bon : on lui fait produire le SQL, on
   l'EXÉCUTE sur une vraie base, et on entre avec le mot de passe
   annoncé. Ce qui est vérifié ici n'est pas un format de texte, c'est
   que la porte s'ouvre.

       node loge/serveur/essai-outil-mdp.mjs
═══════════════════════════════════════════════════════════════════ */
import { DatabaseSync } from 'node:sqlite';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';

const R = new URL('../../', import.meta.url).pathname;
const MDP = 'la colonne du midi';
const sortie = execFileSync('node', [R + 'loge/serveur/nouveau-mdp.mjs',
  'neuf@epreuve.test', MDP, 'tresorerie', 'Officier Neuf'], {encoding:'utf8'});
const insert = sortie.split('── Pour CRÉER un compte ──')[1].trim()
  .split('\n').filter(l => /^(INSERT|VALUES)/.test(l)).join('\n');

const db = new DatabaseSync(':memory:');
db.exec(fs.readFileSync(R + 'loge/serveur/001-socle-en-ligne.sql','utf8'));
db.exec(insert);

const DB = { prepare(sql){ return { _a: [], bind(...a){ this._a = a; return this; },
  async first(){ return db.prepare(sql).get(...this._a) ?? null; },
  async all(){ return { results: db.prepare(sql).all(...this._a) }; },
  async run(){ const r = db.prepare(sql).run(...this._a);
               return { meta: { changes: Number(r.changes) } }; } }; } };
const { onRequestPost: entrer } = await import(R + 'functions/api/entrer.js');
const appel = m => entrer({ env:{DB}, request: new Request('https://x/api/entrer',
  { method:'POST', headers:{'content-type':'application/json'},
    body: JSON.stringify({ mdp: m }) }) });

let ko = 0;
const v = (c,n,d='') => { console.log(`  ${c?'✓':'✗'} ${n}${c?'':'  <- '+d}`); if(!c) ko++; };

let r = await appel(MDP);
v(r.status === 200, "le compte créé par l'outil ouvre vraiment la porte", r.status);
v((await r.json()).charge === 'tresorerie', "avec la charge demandée");
r = await appel('autre chose');
v(r.status === 401, "et un autre mot de passe ne l'ouvre pas", r.status);

/* et le remplacement */
const s2 = execFileSync('node', [R + 'loge/serveur/nouveau-mdp.mjs',
  'neuf@epreuve.test', 'le pavé mosaïque'], {encoding:'utf8'});
const upd = s2.split('── Pour CRÉER')[0].split('\n')
  .filter(l => /^(UPDATE|\s+WHERE)/.test(l)).join('\n');
db.exec(upd);
r = await appel(MDP);
v(r.status === 401, "après remplacement, l'ancien ne vaut plus rien", r.status);
r = await appel('le pavé mosaïque');
v(r.status === 200, "et le neuf ouvre", r.status);

console.log(ko ? `\n  ${ko} échec(s)` : '\n  tout passe');
process.exit(ko ? 1 : 0);
