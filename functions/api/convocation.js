/* ═══════════════════════════════════════════════════════════════════
   LA CONVOCATION DE LA LOGE, VUE PAR UN MEMBRE

   Demandé : que les Sœurs et Frères de BERESHIT puissent consulter la
   convocation de leur prochaine Tenue — et les précédentes — dans
   l'Espace Membres.

   ── POURQUOI ELLE VIENT DU SERVEUR ────────────────────────────────

   Une convocation porte des noms (intervenants, vote d'affiliation) et
   le téléphone du secrétariat. Le dépôt est servi en clair par
   Cloudflare : écrite dans la page ou posée en PDF, elle serait
   publiée. Elle est donc lue dans le registre de la Secrétaire, à la
   demande, contre une adresse connue.

   ── QUI ENTRE, ET CE QUE CELA VAUT ────────────────────────────────

   Une adresse de MEMBRE : au tableau de l'Atelier (actif ou honoraire),
   ou déjà convoqué par le serveur. Comme le Tableau de la Loge, c'est
   une porte avec un nom dessus, non un coffre : qui connaît l'adresse
   d'une Sœur de l'Atelier peut lire sa convocation.

   ── CE QUI SORT D'ICI ─────────────────────────────────────────────

   Une liste blanche de champs de la Tenue, et l'ordre du jour. Pas la
   signature ni le mot d'accueil (ils ne servent qu'au courriel), pas
   le lien de paiement (les colonnes ont réglé avec la capitation), pas
   une adresse de membre.

   ► LES TENUES PASSÉES gardent leur date, leur lieu, leurs heures et
     leurs agapes, mais NON leur ordre du jour : le registre ne le
     classe pas avec elles. On le dit (odj_conserve), on ne l'invente pas.
═══════════════════════════════════════════════════════════════════ */

import { json, noter } from './_commun.js';

const LOGE = 1;                      // un seul Atelier pour l'instant
const ESSAIS_MAX = 30;               // adresses essayées par heure
const MARQUE = 'convocation : adresse inconnue';
const DATE = /^\d{4}-\d{2}-\d{2}$/;

const courrielPlausible = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);
const txt = (v, max = 400) => String(v == null ? '' : v).replace(/[ \t]+/g, ' ').trim().slice(0, max);

async function tropDEssais(context){
  try {
    const r = await context.env.DB.prepare(
      "SELECT COUNT(*) AS n FROM journal WHERE loge_id = ? AND quoi = ? " +
      "AND le > datetime('now','-1 hour')").bind(LOGE, MARQUE).first();
    return Number(r?.n ?? 0) >= ESSAIS_MAX;
  } catch (e) { return false; }
}

async function registre(context){
  try {
    const r = await context.env.DB.prepare(
      'SELECT donnees FROM etat WHERE loge_id = ?').bind(LOGE).first();
    const d = r ? JSON.parse(r.donnees) : null;
    return d && typeof d === 'object' ? d : null;
  } catch (e) { return null; }
}

async function estMembre(context, reg, courriel){
  const auTableau = (reg?.membres || []).some(m =>
    (m.statut === 'actif' || m.statut === 'honoraire') &&
    txt(m.email, 200).toLowerCase() === courriel);
  if (auTableau) return true;
  try {
    const r = await context.env.DB.prepare(
      "SELECT 1 AS ok FROM reponses WHERE loge_id = ? AND qui_type = 'membre' " +
      "AND lower(trim(courriel)) = ? LIMIT 1").bind(LOGE, courriel).first();
    return !!r;
  } catch (e) { return false; }
}

/* La Tenue telle qu'un membre la lit : des champs nommés, un par un. */
function enFeuillet(t, odj){
  return {
    titre: txt(t.titre), degre: Number(t.degre) || null,
    date: DATE.test(t.date) ? t.date : '',
    heureConv: txt(t.heureConv, 10), heureOuv: txt(t.heureOuv, 10),
    lieuNom: txt(t.lieuNom), lieuAdresse: txt(t.lieuAdresse),
    lieuCp: txt(t.lieuCp, 10), lieuVille: txt(t.lieuVille),
    adage: txt(t.adage), agapesOui: !!t.agapesOui,
    agapesPrix: Number(t.agapesPrix) || null,
    agapesLimite: DATE.test(t.agapesLimite) ? t.agapesLimite : '',
    agapesQuiPaie: txt(t.agapesQuiPaie, 600),
    motFin: txt(t.motFin, 1000), contact: txt(t.contact),
    odj: (odj || []).slice(0, 40).map(o => ({ h: txt(o.h, 10), t: txt(o.t, 300) }))
  };
}

export async function onRequestPost(context){
  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  if (!corps || typeof corps !== 'object') return json({ erreur: 'requete_illisible' }, 400);

  const courriel = txt(corps.courriel, 200).toLowerCase();
  if (!courrielPlausible(courriel)) return json({ erreur: 'courriel_manquant' }, 400);
  if (await tropDEssais(context)) return json({ erreur: 'trop_dessais' }, 429);

  const reg = await registre(context);
  if (!(await estMembre(context, reg, courriel))){
    await noter(context, LOGE, null, MARQUE);
    return json({ erreur: 'inconnu' }, 404);
  }

  const courante = reg?.tenue && DATE.test(reg.tenue.date) ? reg.tenue : null;
  const passees = (reg?.tenuesPassees || []).map(a => a?.tenue)
    .filter(t => t && DATE.test(t.date) && (!courante || t.date !== courante.date));
  if (!courante && !passees.length) return json({ erreur: 'aucune_convocation' }, 404);

  const dates = [courante?.date, ...passees.map(t => t.date)].filter(Boolean)
    .sort().reverse();
  const voulue = DATE.test(corps.date || '') && dates.includes(corps.date)
    ? corps.date : (courante ? courante.date : dates[0]);

  const ancienne = voulue !== courante?.date;
  const t = ancienne ? passees.find(p => p.date === voulue) : courante;
  return json({
    tenue: voulue, prevue: courante ? courante.date : null, tenues: dates,
    odj_conserve: !ancienne,
    convocation: enFeuillet(t, ancienne ? [] : reg.odj)
  });
}
