/* ═══════════════════════════════════════════════════════════════════
   CHANGER SON MOT DE PASSE

   Les deux premiers mots de passe ont été choisis par un tiers, dits
   dans un courriel, et écrits — le temps d'une soirée — dans un
   fichier d'épreuve d'un dépôt public. Aucun des trois ne s'efface.
   Ils doivent donc être remplacés par des mots que leur porteur est
   seul à connaître.

   ► ON NE CHANGE QUE LE SIEN. La session dit qui parle ; il n'y a pas
     de champ pour désigner quelqu'un d'autre. Un Officier ne peut pas
     fermer la porte au nez d'un autre.

   ► L'ANCIEN EST REDEMANDÉ. Un téléphone laissé déverrouillé sur une
     table ne doit pas suffire à s'emparer d'un compte.

   ► UN SEUL SEL NEUF. Changer le mot sans changer le sel laisserait
     deviner, de deux empreintes, qu'il s'agit du même compte.

   ► LES AUTRES SESSIONS TOMBENT. Changer son mot de passe sans
     déconnecter qui l'avait déjà ne protège de rien : c'est justement
     l'intrus qu'on veut faire sortir. Celle qui demande le changement
     survit — on ne met pas dehors qui vient de faire le nécessaire.
═══════════════════════════════════════════════════════════════════ */

import { empreinteMdp, memeChaine, sessionCourante, json, noter } from './_commun.js';

const LONGUEUR_MIN = 10;

const hex = t => [...new Uint8Array(t)].map(o => o.toString(16).padStart(2, '0')).join('');

export async function onRequestPost(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const ancien  = typeof corps?.ancien  === 'string' ? corps.ancien.trim()  : '';
  const nouveau = typeof corps?.nouveau === 'string' ? corps.nouveau.trim() : '';

  if (!ancien || !nouveau) return json({ erreur: 'champs_manquants' }, 400);

  /* Ce qu'on refuse, on le dit — un refus muet fait recommencer à
     l'aveugle. Ces règles ne portent que sur le mot choisi : elles
     n'apprennent rien sur celui qui est en place. */
  if ([...nouveau].length < LONGUEUR_MIN)
    return json({ erreur: 'trop_court', minimum: LONGUEUR_MIN }, 400);
  if (nouveau === ancien)
    return json({ erreur: 'identique' }, 400);

  const u = await context.env.DB.prepare(
    'SELECT id, courriel, nom, mdp_hash, mdp_sel, loge_id FROM utilisateurs WHERE id = ?')
    .bind(moi.id).first();
  if (!u) return json({ erreur: 'non_connecte' }, 401);

  if (!memeChaine(await empreinteMdp(ancien, u.mdp_sel), u.mdp_hash)){
    await noter(context, u.loge_id, u.id, 'changement de mot de passe refusé');
    return json({ erreur: 'ancien_faux' }, 403);
  }

  const sel = hex(crypto.getRandomValues(new Uint8Array(16)));
  const h   = await empreinteMdp(nouveau, sel);

  await context.env.DB.prepare(
    'UPDATE utilisateurs SET mdp_hash = ?, mdp_sel = ? WHERE id = ?')
    .bind(h, sel, u.id).run();

  await context.env.DB.prepare(
    'DELETE FROM sessions WHERE utilisateur_id = ? AND jeton_hash <> ?')
    .bind(u.id, moi.jeton_hash).run();

  await noter(context, u.loge_id, u.id, 'mot de passe changé');
  return json({ fait: true });
}
