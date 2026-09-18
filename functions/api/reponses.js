/* ═══════════════════════════════════════════════════════════════════
   RELEVER LES RÉPONSES — côté Secrétariat

   L'autre bout de la chaîne. « reponse.js » s'ouvre sans session pour
   que chacun réponde ; celle-ci exige la session, parce qu'elle donne
   la liste de qui a répondu quoi.

   Deux routes distinctes, et c'est voulu : un lien retrouvé dans une
   boîte aux lettres ne doit pas ouvrir le Tableau de l'Atelier.
═══════════════════════════════════════════════════════════════════ */

import { sessionCourante, json, noter } from './_commun.js';

export async function onRequestGet(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  const u = new URL(context.request.url);
  const tenue = (u.searchParams.get('tenue') || '').trim();
  const toutes = u.searchParams.get('toutes') === '1';

  let sql = 'SELECT jeton, tenue, qui_type, qui_id, nom, courriel, reponse, ' +
            'agapes, repondu_le FROM reponses WHERE loge_id = ? AND reponse IS NOT NULL';
  const liants = [moi.loge_id];
  if (tenue){ sql += ' AND tenue = ?'; liants.push(tenue); }
  if (!toutes) sql += ' AND versee = 0';
  sql += ' ORDER BY repondu_le';

  const { results } = await context.env.DB.prepare(sql).bind(...liants).all();
  return json({ reponses: (results || []).map(r => ({
    jeton: r.jeton, tenue: r.tenue, type: r.qui_type, id: r.qui_id,
    nom: r.nom, courriel: r.courriel, reponse: r.reponse,
    agapes: !!r.agapes, le: r.repondu_le
  })) });
}

/* Marquer comme reprises au registre. Rien n'est effacé : ce qu'une
   personne a répondu elle-même est une trace. */
export async function onRequestPut(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const jetons = Array.isArray(corps?.versees)
    ? corps.versees.filter(j => typeof j === 'string' && /^[a-f0-9]{64}$/.test(j))
                   .slice(0, 500)
    : [];
  if (!jetons.length) return json({ versees: 0 });

  const trous = jetons.map(() => '?').join(',');
  const r = await context.env.DB.prepare(
    `UPDATE reponses SET versee = 1
      WHERE loge_id = ? AND versee = 0 AND jeton IN (${trous})`)
    .bind(moi.loge_id, ...jetons).run();

  const n = r?.meta?.changes ?? 0;
  if (n) await noter(context, moi.loge_id, moi.id,
                     n + ' réponse(s) reprise(s) au registre');
  return json({ versees: n });
}
