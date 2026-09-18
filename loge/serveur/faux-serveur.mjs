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
db.exec(fs.readFileSync(RACINE + 'loge/serveur/002-annuaire.sql', 'utf8'));
db.exec(fs.readFileSync(RACINE + 'loge/serveur/003-envois.sql', 'utf8'));
db.exec(fs.readFileSync(RACINE + 'loge/serveur/004-reponses.sql', 'utf8'));

/* RBI_JETONS_MUETS reproduit la panne la plus traître de la chaîne :
   l'écriture des jetons de réponse ÉCHOUE SANS RIEN DIRE. L'INSERT
   rend la main comme s'il avait posé la ligne, le courriel part avec
   un lien que rien ne connaît, et cent personnes tombent sur « ce
   lien ne mène nulle part » en croyant que c'est leur messagerie.
   Le déclencheur ci-dessous avale les insertions exactement comme le
   ferait une base où 004-reponses.sql n'aurait jamais été joué en
   entier. */
if (process.env.RBI_JETONS_MUETS){
  db.exec(`CREATE TRIGGER reponses_muettes BEFORE INSERT ON reponses
           BEGIN SELECT RAISE(IGNORE); END;`);
}

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

/* ── UN FAUX SERVICE DE COURRIER ───────────────────────────────────
   On n'écrit à personne pendant une épreuve. Les appels vers Brevo et
   Resend sont interceptés ici, et l'on garde ce qui LEUR AURAIT ÉTÉ
   remis : c'est cela qu'on vérifie — la liste, le sujet, le corps.

   RBI_COURRIEL_ECHEC=1 leur fait répondre une erreur, pour éprouver ce
   que le programme fait quand le service refuse. */
const vraiFetch = globalThis.fetch;
globalThis.__courriels = [];
globalThis.fetch = async (url, options) => {
  const u = String(url);
  if (u.includes('api.brevo.com') || u.includes('api.resend.com')){
    let corps = null;
    try { corps = JSON.parse(options && options.body); } catch (e) {}
    globalThis.__courriels.push({ service: u.includes('brevo') ? 'brevo' : 'resend',
                                  corps });
    if (process.env.RBI_COURRIEL_ECHEC)
      return new Response('{"message":"cle refusee"}', { status: 401 });
    return new Response('{"messageId":"epreuve"}', { status: 201 });
  }
  return vraiFetch(url, options);
};

const DB = { prepare(sql){ return {
  _a: [], bind(...a){ this._a = a; return this; },
  async first(){ return db.prepare(sql).get(...this._a) ?? null; },
  async all(){ return { results: db.prepare(sql).all(...this._a) }; },
  async run(){ const r = db.prepare(sql).run(...this._a);
               return { meta: { changes: Number(r.changes) } }; } }; } };

const F = {
  entrer: await import(RACINE + 'functions/api/entrer.js'),
  porte:  await import(RACINE + 'functions/api/porte.js'),
  mdp:    await import(RACINE + 'functions/api/mdp.js'),
  annuaire: await import(RACINE + 'functions/api/annuaire.js'),
  envoyer:  await import(RACINE + 'functions/api/envoyer.js'),
  reponse:  await import(RACINE + 'functions/api/reponse.js'),
  reponses: await import(RACINE + 'functions/api/reponses.js'),
  sortir: await import(RACINE + 'functions/api/sortir.js'),
  etat:   await import(RACINE + 'functions/api/etat.js'),
};

createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  /* « / » sert le programme de gestion : c'est ce que toutes les
     épreuves ouvrent. L'accueil du site, lui, garde son propre chemin
     — sans quoi l'un recouvrirait l'autre. */
  if (u.pathname === '/'){
    res.writeHead(200, {'content-type':'text/html; charset=utf-8'});
    return res.end(fs.readFileSync(PAGE));
  }
  /* L'Espace Membres, pour éprouver le formulaire de l'annuaire là où
     il vit vraiment — et non une imitation qui lui ressemblerait. */
  if (u.pathname === '/reponse.html'){
    res.writeHead(200, {'content-type':'text/html; charset=utf-8'});
    return res.end(fs.readFileSync(RACINE + 'reponse.html'));
  }
  /* L'accueil et ses fichiers : le tuilage du site y vit, et ses
     questions sont dans assets/config.js. On sert le dépôt tel quel,
     en lecture seule et sur des chemins connus — une épreuve doit
     éprouver la vraie page, non une imitation. */
  {
    const m2 = u.pathname.match(
      /^\/(index\.html|assets\/[\w.-]+\.(?:js|css|png|jpe?g|svg|webp))$/);
    if (m2){
      const f = RACINE + m2[1];
      if (fs.existsSync(f)){
        const t = f.endsWith('.js')  ? 'text/javascript'
                : f.endsWith('.css') ? 'text/css'
                : f.endsWith('.html')? 'text/html; charset=utf-8'
                : f.endsWith('.svg') ? 'image/svg+xml' : 'image/*';
        res.writeHead(200, {'content-type': t});
        return res.end(fs.readFileSync(f));
      }
    }
  }
  if (u.pathname === '/espace-membres.html'){
    res.writeHead(200, {'content-type':'text/html; charset=utf-8'});
    return res.end(fs.readFileSync(RACINE + 'espace-membres.html'));
  }
  /* Ce que le faux service a reçu — pour l'épreuve seulement. */
  if (u.pathname === '/__courriels'){
    res.writeHead(200, {'content-type':'application/json'});
    return res.end(JSON.stringify(globalThis.__courriels));
  }
  /* Le contenu brut d'une table — pour DIAGNOSTIQUER une épreuve qui
     échoue, et non pour la faire passer : rien du programme ne l'appelle. */
  if (u.pathname === '/__table'){
    const nom = (u.searchParams.get('nom') || '').replace(/[^a-z_]/g, '');
    res.writeHead(200, {'content-type':'application/json'});
    try { return res.end(JSON.stringify(db.prepare('SELECT * FROM ' + nom).all(),
      (k, v) => typeof v === 'bigint' ? Number(v) : v)); }
    catch (e) { return res.end(JSON.stringify({ erreur: String(e) })); }
  }
  if (u.pathname === '/__courriels/vider'){
    globalThis.__courriels = [];
    res.writeHead(200, {'content-type':'application/json'});
    return res.end('[]');
  }
  const m = u.pathname.match(/^\/api\/(entrer|sortir|etat|porte|mdp|annuaire|envoyer|reponses?)$/);
  if (!m){ res.writeHead(404); return res.end('non'); }

  const corps = await new Promise(ok => { let d=''; req.on('data',c=>d+=c); req.on('end',()=>ok(d)); });
  /* PATHNAME + SEARCH. La chaîne de requête était jetée ici, et les
     fonctions recevaient une adresse nue : « /api/reponse?j=… » leur
     arrivait sans jeton, et elles répondaient « lien inconnu » à un
     lien parfaitement valable. Le défaut était dans le banc d'essai,
     non dans le programme — c'est pire : il faisait échouer ce qui
     marche, et aurait pu faire passer ce qui ne marche pas. */
  const requete = new Request('https://x' + u.pathname + u.search, {
    method: req.method,
    headers: { cookie: req.headers.cookie || '', 'content-type': 'application/json' },
    body: ['GET','HEAD'].includes(req.method) ? undefined : (corps || undefined)
  });
  /* Un faux service de courrier, pour éprouver l'envoi sans écrire à
     personne. RBI_COURRIEL=1 le branche ; sinon la fonction se
     comporte comme sur un site non configuré. */
  const env = { DB };
  if (process.env.RBI_COURRIEL){
    env.BREVO_CLE = 'cle-d-epreuve';
    env.COURRIEL_EXPEDITEUR = 'epreuve@exemple.test';
    env.COURRIEL_NOM = 'Atelier d’épreuve';
    env.COURRIEL_REPONSE = 'reponses@exemple.test';
  }
  const mod = F[m[1]];
  const fn = req.method === 'GET' ? mod.onRequestGet
           : req.method === 'PUT' ? mod.onRequestPut : mod.onRequestPost;
  if (!fn){ res.writeHead(405); return res.end(); }
  try {
    const r = await fn({ env, request: requete });
    const h = {}; r.headers.forEach((v,k) => h[k] = v);
    if (h['set-cookie']) h['set-cookie'] = h['set-cookie'].replace('; Secure','');
    res.writeHead(r.status, h);
    res.end(await r.text());
  } catch (e) { res.writeHead(500); res.end(String(e)); }
}).listen(PORT, () => console.log('serveur d’épreuve sur http://127.0.0.1:' + PORT +
  (process.env.RBI_SANS_COMPTES ? ' — SANS AUCUN COMPTE' : '')));
