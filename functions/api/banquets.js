/* ═══════════════════════════════════════════════════════════════════
   LE MAÎTRE DES BANQUETS : QUI RESTE À TABLE, TENUE PAR TENUE

   Demandé : un onglet réservé au Maître des banquets et à son
   adjoint, qui liste les personnes aux agapes de chaque Tenue —
   membres, visiteurs et Amis de la Loge.

   ── D'OÙ VIENT LA LISTE : TROIS SOURCES, CROISÉES ─────────────────

   ► MEMBRES ET AMIS : la table « reponses », écrite quand les
     convocations partent. Chacun y dit s'il vient et s'il reste.
   ► VISITEURS : « Annoncer ma venue » (table « annuaire »). Cette
     fiche ne porte PAS de champ agapes : le visiteur s'inscrit et
     paie chez HelloAsso, hors de cette base. Un visiteur annoncé qui
     n'a pas répondu à sa convocation est donc « à confirmer » — on
     ne le compte pas à table sur la seule foi de sa venue.
   ► LE CROISEMENT : un visiteur qui figure dans les deux n'est
     compté qu'une fois. Même courriel s'ils en ont un, sinon mêmes
     mots dans le nom, sans accent ni ordre (« Jean Dupont » et
     « DUPONT Jean » sont la même personne).

   ── CE QUI GARDE CETTE PORTE, ET CE QUE CELA VAUT ─────────────────

   Le courriel, comme pour le Tableau : une porte avec un nom dessus,
   non un coffre. La liste des autorisés n'est PAS dans ce fichier —
   le dépôt est servi en clair, et nommer qui tient quelle charge
   serait le publier. Elle vit dans un secret Cloudflare :
   BANQUETS_COURRIELS, adresses séparées par des virgules.

   ── CE QUI SORT D'ICI, ET RIEN DE PLUS ────────────────────────────

   Un nom, une qualité, et où en est le couvert. Ni courriel, ni
   téléphone, ni Loge ni obédience d'un visiteur, ni jeton.
═══════════════════════════════════════════════════════════════════ */

import { json, noter } from './_commun.js';

const LOGE = 1;                      // un seul Atelier pour l'instant
const ESSAIS_MAX = 30;               // adresses essayées par heure
const MARQUE = 'banquets : adresse refusee';
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ORDRE = { membre: 0, visiteur: 1, ami: 2 };

const courrielPlausible = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);
const propre = v => String(v == null ? '' : v).replace(/\s+/g, ' ').trim().slice(0, 200);
const cle = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').split(/\s+/).filter(Boolean).sort().join(' ');

const autorises = env => String(env.BANQUETS_COURRIELS || '').toLowerCase()
  .split(/[,;\s]+/).filter(a => a.includes('@'));

async function tropDEssais(context){
  try {
    const r = await context.env.DB.prepare(
      "SELECT COUNT(*) AS n FROM journal WHERE loge_id = ? AND quoi = ? " +
      "AND le > datetime('now','-1 hour')").bind(LOGE, MARQUE).first();
    return Number(r?.n ?? 0) >= ESSAIS_MAX;
  } catch (e) { return false; }
}

/* La Tenue prévue : celle que la Secrétaire a saisie au registre. */
async function tenuePrevue(context){
  try {
    const r = await context.env.DB.prepare(
      'SELECT donnees FROM etat WHERE loge_id = ?').bind(LOGE).first();
    const d = r ? JSON.parse(r.donnees)?.tenue?.date : null;
    return DATE.test(d) ? d : null;
  } catch (e) { return null; }
}

/* Les annonces de venue, toutes : une fiche reçue est une trace, qu'elle
   ait été versée au carnet ou non. */
async function annonces(context){
  try {
    const { results } = await context.env.DB.prepare(
      "SELECT donnees FROM annuaire WHERE loge_id = ? " +
      "AND source = 'espace-membres-venue' LIMIT 2000").bind(LOGE).all();
    return (results || []).map(r => { try { return JSON.parse(r.donnees); }
      catch (e) { return null; } })
      .filter(f => f && DATE.test(f.tenue_date || ''));
  } catch (e) { return []; }
}

const statut = r => r.reponse === 'excuse' ? 'non'
  : r.agapes === 1 ? 'oui' : r.agapes === 0 ? 'non' : 'a_confirmer';

async function lesGens(context, tenue, fiches){
  const gens = [], parMail = new Map(), parNom = new Map();
  const { results } = await context.env.DB.prepare(
    "SELECT qui_type, nom, courriel, reponse, agapes FROM reponses " +
    "WHERE loge_id = ? AND tenue = ?").bind(LOGE, tenue).all();
  for (const r of (results || [])){
    const p = { nom: propre(r.nom), qualite: r.qui_type, agapes: statut(r), annonce: false };
    gens.push(p);
    const m = propre(r.courriel).toLowerCase();
    if (m) parMail.set(m, p);
    parNom.set(cle(p.nom), p);
  }
  for (const f of fiches.filter(x => x.tenue_date === tenue)){
    const nom = propre(f.prenom + ' ' + f.nom), m = propre(f.email).toLowerCase();
    const deja = (m && parMail.get(m)) || parNom.get(cle(nom));
    if (deja){ deja.annonce = true; continue; }
    gens.push({ nom, qualite: 'visiteur', agapes: 'a_confirmer', annonce: true });
  }
  gens.sort((a, b) => (ORDRE[a.qualite] ?? 9) - (ORDRE[b.qualite] ?? 9)
    || a.nom.localeCompare(b.nom, 'fr'));
  return gens;
}

export async function onRequestPost(context){
  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  if (!corps || typeof corps !== 'object') return json({ erreur: 'requete_illisible' }, 400);

  const courriel = propre(corps.courriel).toLowerCase();
  if (!courrielPlausible(courriel)) return json({ erreur: 'courriel_manquant' }, 400);

  /* Aucune adresse autorisée n'est posée : on le dit, sans rien montrer. */
  const permis = autorises(context.env);
  if (!permis.length) return json({ erreur: 'non_configure' }, 503);

  if (await tropDEssais(context)) return json({ erreur: 'trop_dessais' }, 429);
  if (!permis.includes(courriel)){
    await noter(context, LOGE, null, MARQUE);
    return json({ erreur: 'refuse' }, 403);
  }

  const prevue = await tenuePrevue(context), fiches = await annonces(context);
  const toutes = new Set(fiches.map(f => f.tenue_date));
  if (prevue) toutes.add(prevue);
  try {
    const { results } = await context.env.DB.prepare(
      'SELECT DISTINCT tenue FROM reponses WHERE loge_id = ?').bind(LOGE).all();
    (results || []).forEach(r => DATE.test(r.tenue) && toutes.add(r.tenue));
  } catch (e) { /* la table des réponses manque : on s'en tient aux annonces */ }
  const tenues = [...toutes].sort().reverse();

  const tenue = DATE.test(corps.tenue || '') && toutes.has(corps.tenue)
    ? corps.tenue : (prevue || tenues[0] || null);
  if (!tenue) return json({ erreur: 'aucune_tenue' }, 404);

  const gens = await lesGens(context, tenue, fiches).catch(() => []);
  const compte = { oui: 0, non: 0, a_confirmer: 0, membre: 0, visiteur: 0, ami: 0 };
  for (const g of gens){
    compte[g.agapes]++;
    if (g.agapes === 'oui' && g.qualite in compte) compte[g.qualite]++;
  }
  return json({ tenue, prevue, tenues, gens, compte });
}
