/* Un serveur qui sert la page ET exécute les vraies fonctions Pages
   sur une vraie base SQLite. C'est le seul moyen d'éprouver ce que
   verront Martine et Sam : l'artefact et le fichier local n'ont pas
   d'API, et je ne peux pas atteindre le site. */
import { createServer } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';

/* Tout se lit dans le dépôt : l'épreuve doit se rejouer sur n'importe
   quelle machine, et non sur la seule où traînaient des fichiers. */
const RACINE = new URL('../../', import.meta.url).pathname;
const PAGE = process.env.RBI_PAGE || RACINE + 'secretariat.html';
const PORT = Number(process.env.RBI_PORT || 8787);

const db = new DatabaseSync(':memory:');
db.exec(fs.readFileSync(RACINE + 'loge/serveur/001-socle-en-ligne.sql', 'utf8'));

/* RBI_SANS_COMPTES reproduit la panne du premier soir : le serveur
   répond, la base est en place, mais la table des utilisateurs est
   vide — et le serveur refuse alors TOUT LE MONDE. C'est le cas que
   la porte doit savoir traverser. */
if (!process.env.RBI_SANS_COMPTES){
  /* ── LES COMPTES D'ÉPREUVE SONT INVENTÉS ───────────────────────────
   Ce fichier portait les vraies adresses de la Sœur Secrétaire et du
   Frère Trésorier, et les empreintes PBKDF2 de leurs vrais mots de
   passe. Or Cloudflare Pages sert TOUT ce que porte le dépôt : ce
   fichier était lisible sur le site. Une empreinte salée à cent mille
   tours ne se renverse pas, mais elle se VÉRIFIE — qui l'a peut
   essayer autant de mots qu'il veut, sans que rien ne l'en empêche, et
   « le nom de famille de la Secrétaire » n'est pas un mot rare.
   Les comptes ci-dessous n'existent nulle part ailleurs. */
db.exec(`INSERT INTO utilisateurs (loge_id, courriel, nom, charge, mdp_hash, mdp_sel) VALUES
(1,'secretariat@epreuve.test','Sœur Secrétaire d’épreuve','secretariat','5570bc41b122b980f0680c90992ed99b5bc55d6cafd02ced6ad321899836debc','540655985750cb2b588fb0ec31f0e412'),
(1,'tresorerie@epreuve.test','Frère Trésorier d’épreuve','tresorerie','b031d6c36d967c5c76b0976d2b0884e5a92ab94aa45219a7e944e58ebccd311f','32c92cf1e3e315596c33adab03b97b8b');`);
}

const DB = { prepare(sql){ return {
  _a: [], bind(...a){ this._a = a; return this; },
  async first(){ return db.prepare(sql).get(...this._a) ?? null; },
  async all(){ return { results: db.prepare(sql).all(...this._a) }; },
  async run(){ const r = db.prepare(sql).run(...this._a);
               return { meta: { changes: Number(r.changes) } }; } }; } };

const F = {
  entrer: await import(RACINE + 'functions/api/entrer.js'),
  sortir: await import(RACINE + 'functions/api/sortir.js'),
  etat:   await import(RACINE + 'functions/api/etat.js'),
};

createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname === '/' || u.pathname === '/index.html'){
    res.writeHead(200, {'content-type':'text/html; charset=utf-8'});
    return res.end(fs.readFileSync(PAGE));
  }
  const m = u.pathname.match(/^\/api\/(entrer|sortir|etat)$/);
  if (!m){ res.writeHead(404); return res.end('non'); }

  const corps = await new Promise(ok => { let d=''; req.on('data',c=>d+=c); req.on('end',()=>ok(d)); });
  const requete = new Request('https://x' + u.pathname, {
    method: req.method,
    headers: { cookie: req.headers.cookie || '', 'content-type': 'application/json' },
    body: ['GET','HEAD'].includes(req.method) ? undefined : (corps || undefined)
  });
  const mod = F[m[1]];
  const fn = req.method === 'GET' ? mod.onRequestGet
           : req.method === 'PUT' ? mod.onRequestPut : mod.onRequestPost;
  if (!fn){ res.writeHead(405); return res.end(); }
  try {
    const r = await fn({ env: { DB }, request: requete });
    const h = {}; r.headers.forEach((v,k) => h[k] = v);
    if (h['set-cookie']) h['set-cookie'] = h['set-cookie'].replace('; Secure','');
    res.writeHead(r.status, h);
    res.end(await r.text());
  } catch (e) { res.writeHead(500); res.end(String(e)); }
}).listen(PORT, () => console.log('serveur d’épreuve sur http://127.0.0.1:' + PORT +
  (process.env.RBI_SANS_COMPTES ? ' — SANS AUCUN COMPTE' : '')));
