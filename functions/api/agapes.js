/* ═══════════════════════════════════════════════════════════════════
   LES AGAPES, VUES DU SECRÉTARIAT

   Même liste que celle du Maître des banquets (/api/banquets) : ce
   fichier n'en est que l'entrée « avec session », celle du programme
   du Secrétariat. Les deux écrivent dans les MÊMES tables :

     banquets_paye    qui a payé, par Tenue et par nom
     banquets_noms    les noms que le Maître des banquets a ajoutés
     banquets_prevus  le nombre attendu

   Ce que l'un coche, l'autre le voit : il n'y a qu'une copie.

   GET   -> { tenue, payes: [cle…], noms: [{cle, nom, qualite}], attendus }
   POST  -> { marquer: {cle, paye} } | { ajouter: {nom, qualite} }
          | { retirer: {cle} } | { prevus: n }     (puis la même réponse)
═══════════════════════════════════════════════════════════════════ */
import { json, sessionCourante } from './_commun.js';
import { propre, tenuePrevue, marques, manuels, attendus, ecrire, cocher }
  from './banquets.js';

async function etat(context, tenue){
  return json({
    tenue,
    payes: [...await marques(context, tenue)],
    noms: await manuels(context, tenue),
    attendus: await attendus(context, tenue),
  });
}

export async function onRequest(context){
  const moi = await sessionCourante(context).catch(() => null);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);
  const tenue = await tenuePrevue(context);
  if (!tenue) return json({ erreur: 'aucune_tenue' }, 404);

  if (context.request.method === 'GET') return etat(context, tenue);
  if (context.request.method !== 'POST') return json({ erreur: 'methode' }, 405);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  if (!corps || typeof corps !== 'object') return json({ erreur: 'requete_illisible' }, 400);

  const m = corps.marquer;
  if (m && typeof m === 'object'){
    const k = propre(m.cle).slice(0, 120);
    if (!k || typeof m.paye !== 'boolean') return json({ erreur: 'requete_illisible' }, 400);
    await cocher(context, tenue, k, m.paye);
  }
  if (corps.ajouter || corps.retirer || corps.prevus !== undefined)
    await ecrire(context, tenue, corps).catch(() => {});
  return etat(context, tenue);
}
