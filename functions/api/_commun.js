/* ═══════════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — ce que partagent les fonctions du serveur

   Ce fichier commence par un souligné : Cloudflare Pages ne lui donne
   donc aucune adresse. Il s'importe, il ne s'appelle pas.

   ► LE MOT DE PASSE N'EST JAMAIS ÉCRIT NULLE PART. La base ne garde
     qu'une empreinte PBKDF2 salée : 100 000 tours, un sel de seize
     octets propre à chacun. Qui lirait la base n'y trouverait aucun
     mot de passe, et deux mots de passe identiques y donneraient deux
     empreintes différentes.

   ► LE JETON DE SESSION NON PLUS. Le navigateur reçoit le jeton ; la
     base n'en garde que l'empreinte. Une base dérobée ne permet donc
     pas de se faire passer pour quelqu'un.

   ► LA COMPARAISON EST À TEMPS CONSTANT. Comparer deux empreintes avec
     === renseigne, par le temps que met la machine à répondre, sur le
     nombre de caractères déjà justes. C'est peu, et c'est assez.
═══════════════════════════════════════════════════════════════════ */

const TOURS = 100000;
const DUREE_SESSION_H = 12;

const hex = tampon => [...new Uint8Array(tampon)]
  .map(o => o.toString(16).padStart(2, '0')).join('');

const octets = h => new Uint8Array(
  (h.match(/.{1,2}/g) || []).map(p => parseInt(p, 16)));

export async function empreinteMdp(mdp, selHex){
  const cle = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(mdp), 'PBKDF2', false, ['deriveBits']);
  const brut = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt: octets(selHex), iterations: TOURS, hash: 'SHA-256' },
    cle, 256);
  return hex(brut);
}

export async function empreinteJeton(jeton){
  return hex(await crypto.subtle.digest(
    'SHA-256', new TextEncoder().encode(jeton)));
}

/* Le temps de réponse ne doit rien apprendre : on parcourt toujours
   les deux chaînes en entier. */
export function memeChaine(a, b){
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  let ecart = 0;
  for (let i = 0; i < a.length; i++) ecart |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return ecart === 0;
}

export function nouveauJeton(){
  return hex(crypto.getRandomValues(new Uint8Array(32)));
}

export function expiration(){
  return new Date(Date.now() + DUREE_SESSION_H * 3600e3).toISOString();
}

export function biscuit(jeton, secondes){
  return `rbi_session=${jeton}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${secondes}`;
}

export function jetonDuBiscuit(requete){
  const brut = requete.headers.get('cookie') || '';
  const m = brut.match(/(?:^|;\s*)rbi_session=([a-f0-9]{64})(?:;|$)/);
  return m ? m[1] : null;
}

export function json(donnees, statut = 200, entetes = {}){
  return new Response(JSON.stringify(donnees), {
    status: statut,
    headers: { 'content-type': 'application/json; charset=utf-8',
               'cache-control': 'no-store', ...entetes }
  });
}

/* Qui est là ? null si personne. La session périmée est refusée, et
   effacée au passage : une table de sessions qui enfle indéfiniment
   finit par coûter plus que le service qu'elle rend. */
export async function sessionCourante(context){
  const jeton = jetonDuBiscuit(context.request);
  if (!jeton) return null;
  const h = await empreinteJeton(jeton);
  const r = await context.env.DB.prepare(
    `SELECT s.jeton_hash, s.expire_le, u.id, u.nom, u.charge, u.loge_id, u.actif
       FROM sessions s JOIN utilisateurs u ON u.id = s.utilisateur_id
      WHERE s.jeton_hash = ?`).bind(h).first();
  if (!r) return null;
  if (!r.actif || new Date(r.expire_le) < new Date()){
    await context.env.DB.prepare('DELETE FROM sessions WHERE jeton_hash = ?')
      .bind(h).run();
    return null;
  }
  return { id: r.id, nom: r.nom, charge: r.charge, loge_id: r.loge_id, jeton_hash: h };
}

export async function noter(context, loge_id, utilisateur_id, quoi){
  try {
    await context.env.DB.prepare(
      'INSERT INTO journal (loge_id, utilisateur_id, quoi) VALUES (?, ?, ?)')
      .bind(loge_id, utilisateur_id, quoi).run();
  } catch (e) { /* le journal ne doit jamais faire échouer l'acte qu'il consigne */ }
}
