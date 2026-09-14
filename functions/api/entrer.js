/* ═══════════════════════════════════════════════════════════════════
   OUVRIR UNE SESSION

   La Sœur Secrétaire et le Trésorier tapent un mot de passe, et rien
   d'autre : c'est ce qu'on leur a dit, et ce qui tient sur un
   téléphone un soir de tenue. Le mot de passe vaut donc à la fois
   preuve et identité — acceptable à deux comptes, à revoir au-delà :
   le jour où l'Atelier en aura dix, il faudra demander le courriel.

   ► On éprouve TOUS les comptes, même après en avoir trouvé un. Sortir
     à la première réussite dirait, par le temps de réponse, quelque
     chose sur le compte trouvé.

   ► Le message d'échec ne distingue jamais « mot de passe inconnu » de
     « compte désactivé ». Ce que le refus n'apprend pas ne se devine
     pas.
═══════════════════════════════════════════════════════════════════ */

import { empreinteMdp, empreinteJeton, memeChaine, nouveauJeton,
         expiration, biscuit, json, noter } from './_commun.js';

export async function onRequestPost(context){
  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const mdp = typeof corps?.mdp === 'string' ? corps.mdp.trim() : '';
  if (!mdp) return json({ erreur: 'mot_de_passe_manquant' }, 400);

  const { results } = await context.env.DB.prepare(
    'SELECT id, nom, charge, loge_id, mdp_hash, mdp_sel, actif FROM utilisateurs')
    .all();

  let trouve = null;
  for (const u of (results || [])){
    const h = await empreinteMdp(mdp, u.mdp_sel);
    if (memeChaine(h, u.mdp_hash) && u.actif) trouve = u;   // pas de break
  }

  if (!trouve){
    await noter(context, null, null, 'entrée refusée');
    return json({ erreur: 'refus' }, 401);
  }

  const jeton = nouveauJeton();
  await context.env.DB.prepare(
    'INSERT INTO sessions (jeton_hash, utilisateur_id, expire_le) VALUES (?, ?, ?)')
    .bind(await empreinteJeton(jeton), trouve.id, expiration()).run();

  await noter(context, trouve.loge_id, trouve.id, 'entrée');

  return json({ nom: trouve.nom, charge: trouve.charge },
              200, { 'set-cookie': biscuit(jeton, 12 * 3600) });
}
