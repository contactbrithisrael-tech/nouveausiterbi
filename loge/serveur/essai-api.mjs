/* Une imitation de D1 sur SQLite, pour éprouver les fonctions du
   serveur telles qu'elles seront exécutées. */
import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';

const db = new DatabaseSync(':memory:');
const RACINE = new URL('../../', import.meta.url).pathname;
db.exec(fs.readFileSync(RACINE + 'loge/serveur/001-socle-en-ligne.sql','utf8'));
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

const DB = {
  prepare(sql){
    return {
      _a: [],
      bind(...a){ this._a = a; return this; },
      async first(){ return db.prepare(sql).get(...this._a) ?? null; },
      async all(){ return { results: db.prepare(sql).all(...this._a) }; },
      async run(){ const r = db.prepare(sql).run(...this._a);
                   return { meta: { changes: Number(r.changes) } }; }
    };
  }
};

const ctx = (req) => ({ env: { DB }, request: req });
const req = (m, corps, biscuit) => new Request('https://x/api/x', {
  method: m,
  headers: biscuit ? { cookie: biscuit, 'content-type': 'application/json' }
                   : { 'content-type': 'application/json' },
  body: corps === undefined ? undefined : JSON.stringify(corps)
});

const { onRequestPost: entrer } = await import(RACINE + 'functions/api/entrer.js');
const { onRequestPost: sortir } = await import(RACINE + 'functions/api/sortir.js');
const { onRequestGet: lire, onRequestPut: ecrire } = await import(RACINE + 'functions/api/etat.js');
const { onRequestGet: etatPorte } = await import(RACINE + 'functions/api/porte.js');
const { onRequestPost: changerMdp } = await import(RACINE + 'functions/api/mdp.js');

let ko = 0;
const v = (c, nom, d='') => { console.log(`  ${c?'✓':'✗'} ${nom}${c?'':'  <- '+JSON.stringify(d)}`); if(!c) ko++; };

// ── entrer
let r = await entrer(ctx(req('POST', { mdp: 'nimportequoi' })));
v(r.status === 401, "un mot de passe faux est refusé", r.status);

r = await entrer(ctx(req('POST', { mdp: 'cleSecretariatEpreuve' })));
let j = await r.json();
v(r.status === 200 && j.charge === 'secretariat', "la clé du Secrétariat ouvre", j);
const bM = r.headers.get('set-cookie').split(';')[0];
v(/^rbi_session=[a-f0-9]{64}$/.test(bM), "un jeton de 32 octets est remis");
v(/HttpOnly/.test(r.headers.get('set-cookie')) && /Secure/.test(r.headers.get('set-cookie'))
  && /SameSite=Strict/.test(r.headers.get('set-cookie')),
  "le biscuit est HttpOnly, Secure, SameSite=Strict");
v(db.prepare('select jeton_hash from sessions').get().jeton_hash !== bM.split('=')[1],
  "la base ne garde QUE l'empreinte du jeton, jamais le jeton");

r = await entrer(ctx(req('POST', { mdp: 'cleTresorerieEpreuve' })));
const bS = r.headers.get('set-cookie').split(';')[0];
v((await r.json()).charge === 'tresorerie', "la clé de la Trésorerie ouvre l'autre charge");

// ── sans session
r = await lire(ctx(req('GET', undefined)));
v(r.status === 401, "sans session, rien n'est servi", r.status);
r = await ecrire(ctx(req('PUT', { donnees: {a:1}, version: 0 })));
v(r.status === 401, "ni écrit", r.status);

// ── l'état partagé
r = await lire(ctx(req('GET', undefined, bM)));
j = await r.json();
v(j.version === 0 && j.donnees === null, "au départ, aucun état : version 0", j);

r = await ecrire(ctx(req('PUT', { donnees: { membres: [{nom:'ESSAI'}] }, version: 0 }, bM)));
j = await r.json();
v(r.status === 200 && j.version === 1, "la Secrétaire écrit : version 1", j);

// ── LE POINT CRUCIAL : le Trésorier voit son travail
r = await lire(ctx(req('GET', undefined, bS)));
j = await r.json();
v(j.version === 1 && j.donnees.membres[0].nom === 'ESSAI',
  "le TRÉSORIER lit ce que la SECRÉTAIRE a écrit", j);

// ── et ne peut pas l'écraser à l'aveugle
r = await ecrire(ctx(req('PUT', { donnees: { membres: [] }, version: 1 }, bS)));
v((await r.json()).version === 2, "il écrit à son tour : version 2");

r = await ecrire(ctx(req('PUT', { donnees: { membres: [{nom:'ÉCRASÉ'}] }, version: 1 }, bM)));
j = await r.json();
v(r.status === 409 && j.erreur === 'conflit',
  "une écriture fondée sur une version périmée est REFUSÉE", j);
v(j.version === 2 && Array.isArray(j.donnees.membres),
  "et le refus rend l'état à jour, pour ne rien perdre", j);
v(db.prepare('select donnees from etat where loge_id=1').get().donnees === '{"membres":[]}',
  "le travail du Trésorier n'a pas été écrasé");

// ── journal
const n = db.prepare('select count(*) c from journal').get().c;
v(Number(n) >= 5, "chaque acte est consigné au journal", n);
const refus = db.prepare("select count(*) c from journal where quoi like '%périmée%'").get().c;
v(Number(refus) === 1, "le refus aussi", refus);

// ── l'état de la porte : juste de quoi savoir si un refus veut dire
//    quelque chose. Un nombre, et rien d'autre.
r = await etatPorte(ctx(req('GET', undefined)));
j = await r.json();
v(r.status === 200 && j.serveur === true && j.comptes === 2,
  "la porte dit combien de comptes le serveur peut reconnaître", j);
v(!('courriel' in j) && !('nom' in j) && !JSON.stringify(j).includes('epreuve.test'),
  "et rien de plus : ni nom, ni adresse, ni empreinte", j);

// ── changer son mot de passe
r = await changerMdp(ctx(req('POST', { ancien:'x', nouveau:'yyyyyyyyyy' })));
v(r.status === 401, "sans session, on ne change le mot de passe de personne", r.status);

r = await changerMdp(ctx(req('POST', { ancien:'faux', nouveau:'un mot bien plus long' }, bM)));
v(r.status === 403 && (await r.json()).erreur === 'ancien_faux',
  "l'ancien mot de passe est redemandé, et vérifié", r.status);

r = await changerMdp(ctx(req('POST', { ancien:'cleSecretariatEpreuve', nouveau:'court' }, bM)));
v(r.status === 400 && (await r.json()).erreur === 'trop_court',
  "un mot de passe trop court est refusé", r.status);

// une seconde session de la Secrétaire, ouverte ailleurs
r = await entrer(ctx(req('POST', { mdp: 'cleSecretariatEpreuve' })));
const bM2 = r.headers.get('set-cookie').split(';')[0];
const selAvant = db.prepare('select mdp_sel from utilisateurs where charge=?')
  .get('secretariat').mdp_sel;

r = await changerMdp(ctx(req('POST',
  { ancien:'cleSecretariatEpreuve', nouveau:'le cèdre du Liban en hiver' }, bM2)));
v(r.status === 200 && (await r.json()).fait === true, "le changement aboutit", r.status);
v(db.prepare('select mdp_sel from utilisateurs where charge=?').get('secretariat').mdp_sel
  !== selAvant, "LE SEL EST NEUF LUI AUSSI : deux empreintes ne se recoupent pas");

r = await entrer(ctx(req('POST', { mdp: 'cleSecretariatEpreuve' })));
v(r.status === 401, "L'ANCIEN MOT DE PASSE NE VAUT PLUS RIEN", r.status);
r = await entrer(ctx(req('POST', { mdp: 'le cèdre du Liban en hiver' })));
v(r.status === 200 && (await r.json()).charge === 'secretariat',
  "le nouveau ouvre la même charge", r.status);

// la session qui a fait le changement survit, les autres tombent
r = await lire(ctx(req('GET', undefined, bM2)));
v(r.status === 200, "la session qui a changé le mot de passe survit", r.status);
r = await lire(ctx(req('GET', undefined, bM)));
v(r.status === 401,
  "MAIS LES AUTRES SESSIONS TOMBENT : changer sans déconnecter ne protège de rien",
  r.status);

// le Trésorier n'a pas été touché
r = await entrer(ctx(req('POST', { mdp: 'cleTresorerieEpreuve' })));
v(r.status === 200, "le compte de l'autre Officier est intact", r.status);

// ── sortir
r = await sortir(ctx(req('POST', undefined, bM2)));
v(/Max-Age=0/.test(r.headers.get('set-cookie')), "sortir efface le biscuit");
r = await lire(ctx(req('GET', undefined, bM2)));
v(r.status === 401, "et la session ne vaut plus rien", r.status);

console.log(ko ? `\n  ${ko} échec(s)` : '\n  tout passe');
process.exit(ko ? 1 : 0);
