/* Fermer la session : on efface le jeton de la base ET du navigateur.
   N'effacer que le biscuit laisserait une session ouvrable par qui
   aurait noté le jeton. */
import { jetonDuBiscuit, empreinteJeton, biscuit, json, noter } from './_commun.js';

export async function onRequestPost(context){
  const jeton = jetonDuBiscuit(context.request);
  if (jeton){
    const h = await empreinteJeton(jeton);
    const s = await context.env.DB.prepare(
      'SELECT utilisateur_id FROM sessions WHERE jeton_hash = ?').bind(h).first();
    await context.env.DB.prepare('DELETE FROM sessions WHERE jeton_hash = ?')
      .bind(h).run();
    if (s) await noter(context, null, s.utilisateur_id, 'sortie');
  }
  return json({ sorti: true }, 200,
              { 'set-cookie': 'rbi_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0' });
}
