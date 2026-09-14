/* Un serveur qui sert la page ET exécute les vraies fonctions Pages
   sur une vraie base SQLite. C'est le seul moyen d'éprouver ce que
   verront Martine et Sam : l'artefact et le fichier local n'ont pas
   d'API, et je ne peux pas atteindre le site. */
import { createServer } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';

const S = '/tmp/claude-0/-home-user-nouveausiterbi/7d130877-bf16-5b1d-941f-2441fd899f8b/scratchpad';
const db = new DatabaseSync(':memory:');
db.exec(fs.readFileSync('/tmp/socle.sql', 'utf8'));
db.exec(`INSERT INTO utilisateurs (loge_id, courriel, nom, charge, mdp_hash, mdp_sel) VALUES
(1,'habertmartine@gmail.com','Martine HABERT','secretariat','da9fbc9372c41c342f48470f83dbf88dd877f56939db1693564dae40a54efa79','e73c3b53c491a7b0508f50bc83320eca'),
(1,'samkhanafer13730@gmail.com','Sam','tresorerie','6ce9c78bd13052341c4a1a385f4fb413e317f6b2bdb31f394f5039c2b7497b0f','b490b2a97f25cd9290d86a6b15241933');`);

const DB = { prepare(sql){ return {
  _a: [], bind(...a){ this._a = a; return this; },
  async first(){ return db.prepare(sql).get(...this._a) ?? null; },
  async all(){ return { results: db.prepare(sql).all(...this._a) }; },
  async run(){ const r = db.prepare(sql).run(...this._a);
               return { meta: { changes: Number(r.changes) } }; } }; } };

const F = {
  entrer: await import('/home/user/nouveausiterbi/functions/api/entrer.js'),
  sortir: await import('/home/user/nouveausiterbi/functions/api/sortir.js'),
  etat:   await import('/home/user/nouveausiterbi/functions/api/etat.js'),
};

createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname === '/' || u.pathname === '/index.html'){
    res.writeHead(200, {'content-type':'text/html; charset=utf-8'});
    return res.end(fs.readFileSync(S + '/beta.html'));
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
}).listen(8787, () => console.log('serveur d’épreuve sur http://127.0.0.1:8787'));
