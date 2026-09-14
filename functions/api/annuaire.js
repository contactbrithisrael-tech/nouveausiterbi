/* ═══════════════════════════════════════════════════════════════════
   L'ANNUAIRE — DÉPOSER, ET RELEVER

   POST — sans session. C'est le formulaire de l'Espace Membres qui
   écrit ici, et il écrit depuis le navigateur d'un Frère, pas depuis
   une session d'Officier.

   Cette route est atteignable sans jamais charger la page : le
   tuilage garde le seuil de l'Espace Membres, il ne garde pas une
   adresse HTTP. Ce qui arrive ici est donc traité comme ce que c'est
   — une déclaration, pas une identité établie. On la borne, on la
   range dans sa propre table, et le carnet des Visiteurs la recevra
   avec sa case « Tuilé par » VIDE : le Rite a déjà prévu qui répond
   de l'introduction d'un Visiteur dans le Temple, et ce n'est pas un
   formulaire.

   GET — avec session. Rend les fiches qui n'ont pas encore rejoint le
   carnet, et le compte de celles qui y sont déjà.

   PUT — avec session. Marque comme versées celles dont on donne les
   numéros. Rien n'est effacé : une fiche reçue est une trace.
═══════════════════════════════════════════════════════════════════ */

import { sessionCourante, json, noter } from './_commun.js';

const LOGE = 1;                    // un seul Atelier pour l'instant
const POIDS_MAX = 8 * 1024;        // une fiche, pas un fichier
const EN_ATTENTE_MAX = 300;        // au-delà, on cesse d'accepter
const CHAMP_MAX = 400;

/* Les seuls champs retenus. Ce qui n'est pas dans cette liste est
   jeté : un formulaire public ne décide pas de ce que porte la base. */
const CHAMPS = ['prenom','nom','email','telephone','ville','pays','grade',
                'loge','obedience','rite','dispo_notes','jours','souhaits',
                'accord_partage'];

const texte = v => {
  if (Array.isArray(v)) v = v.join(', ');
  if (typeof v === 'boolean') return v ? 'oui' : '';
  if (v === null || v === undefined) return '';
  return String(v).replace(/\s+/g, ' ').trim().slice(0, CHAMP_MAX);
};

/* Un courriel reconnaissable, sans prétendre valider ce qui ne se
   valide qu'en écrivant à l'adresse. */
const courrielPlausible = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);

export async function onRequestPost(context){
  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  if (!corps || typeof corps !== 'object')
    return json({ erreur: 'requete_illisible' }, 400);

  const fiche = {};
  for (const c of CHAMPS){ const v = texte(corps[c]); if (v) fiche[c] = v; }

  /* De quoi savoir de qui il s'agit et comment le joindre. Sans cela,
     la fiche n'apprend rien et n'encombre que la base. */
  if (!fiche.nom || !fiche.prenom) return json({ erreur: 'nom_manquant' }, 400);
  if (!fiche.email || !courrielPlausible(fiche.email))
    return json({ erreur: 'courriel_manquant' }, 400);

  const brut = JSON.stringify(fiche);
  if (brut.length > POIDS_MAX) return json({ erreur: 'trop_gros' }, 413);

  /* Une file qui n'a pas été relevée depuis longtemps ne doit pas
     pouvoir être gonflée sans fin. On refuse, et on le dit : le
     formulaire retombe alors sur le courriel, qui arrive toujours. */
  const attente = await context.env.DB.prepare(
    'SELECT COUNT(*) AS n FROM annuaire WHERE loge_id = ? AND versee = 0')
    .bind(LOGE).first();
  if (Number(attente?.n ?? 0) >= EN_ATTENTE_MAX)
    return json({ erreur: 'file_pleine' }, 429);

  await context.env.DB.prepare(
    'INSERT INTO annuaire (loge_id, source, donnees) VALUES (?, ?, ?)')
    .bind(LOGE, texte(corps.source) || 'espace-membres', brut).run();

  await noter(context, LOGE, null, 'fiche reçue de l’annuaire');
  return json({ recue: true });
}

export async function onRequestGet(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  const { results } = await context.env.DB.prepare(
    'SELECT id, recu_le, source, donnees FROM annuaire ' +
    'WHERE loge_id = ? AND versee = 0 ORDER BY id').bind(moi.loge_id).all();

  const fiches = [];
  for (const r of (results || [])){
    let d = null;
    try { d = JSON.parse(r.donnees); } catch (e) { continue; }  // illisible : on passe
    fiches.push({ id: r.id, recu_le: r.recu_le, source: r.source, fiche: d });
  }
  return json({ fiches });
}

export async function onRequestPut(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const ids = Array.isArray(corps?.versees)
    ? corps.versees.filter(Number.isInteger).slice(0, 500) : [];
  if (!ids.length) return json({ versees: 0 });

  const trous = ids.map(() => '?').join(',');
  const r = await context.env.DB.prepare(
    `UPDATE annuaire SET versee = 1, versee_le = datetime('now')
      WHERE loge_id = ? AND versee = 0 AND id IN (${trous})`)
    .bind(moi.loge_id, ...ids).run();

  const n = r?.meta?.changes ?? 0;
  if (n) await noter(context, moi.loge_id, moi.id,
                     n + ' fiche(s) de l’annuaire versée(s) au carnet');
  return json({ versees: n });
}
