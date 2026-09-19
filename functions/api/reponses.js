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

  /* ── LES LIENS SONT-ILS SEULEMENT POSÉS ? ─────────────────────────
     La liste ci-dessous ne rend que ceux qui ONT RÉPONDU. Elle est
     donc vide dans deux cas qu'on ne peut pas distinguer : personne
     n'a encore répondu, ou aucun lien n'a jamais été enregistré — et
     alors tous les liens envoyés sont morts, sans que rien ne le
     dise.

     Ce compte-ci les sépare. Il ne rend que des NOMBRES : ni nom, ni
     adresse, ni jeton. De quoi répondre « les liens sont en place »
     ou « il n'y en a aucun », et rien de plus. */
  if (u.searchParams.get('compte') === '1'){
    let sqlC = 'SELECT COUNT(*) AS liens, ' +
               'SUM(CASE WHEN reponse IS NOT NULL THEN 1 ELSE 0 END) AS repondu ' +
               'FROM reponses WHERE loge_id = ?';
    const lc = [moi.loge_id];
    if (tenue){ sqlC += ' AND tenue = ?'; lc.push(tenue); }
    try {
      const r = await context.env.DB.prepare(sqlC).bind(...lc).first();
      return json({ compte: {
        tenue: tenue || null,
        liens: Number(r?.liens || 0),
        repondu: Number(r?.repondu || 0) } });
    } catch (e) {
      /* La table elle-même manque : c'est la réponse la plus utile
         qu'on puisse rendre, et celle qu'on avalait jusqu'ici. */
      return json({ erreur: 'registre_illisible',
        detail: 'La table des réponses n’a pas pu être lue. ' +
                'Vérifiez que 004-reponses.sql a été joué sur la base.' }, 500);
    }
  }

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
