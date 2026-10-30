/* ═══════════════════════════════════════════════════════════════════
   DÉPOSER LA CONVOCATION DE SA LOGE : UNE IMAGE, LE NOM, ET C'EST TOUT

   Une Loge amie dépose sa convocation en image ou en PDF. Rien ne part
   vers les membres d'ici : le dépôt attend dans la table
   « depots_convocation » que le Secrétariat le valide ou le refuse
   (route « depots »), puis l'envoie d'un clic.

   ► CE QU'ON ACCEPTE, ET COMMENT ON LE SAIT. Le type est reconnu à
     l'en-tête du fichier (PNG, JPEG, WebP, PDF), jamais au nom ni à
     ce que le navigateur annonce.
   ► LE POIDS. Une ligne D1 tient 2 Mo et le base64 enfle d'un tiers :
     1,3 Mo de fichier au plus. La page réduit les photos avant l'envoi.
   ► CONTRE LE REMPLISSAGE. Dix dépôts par heure pour l'Atelier, puis
     on refuse, pour tout le monde, jusqu'à l'heure suivante.
═══════════════════════════════════════════════════════════════════ */

import { json, noter } from './_commun.js';

const LOGE = 1;                       // un seul Atelier pour l'instant
const OCTETS_MAX = 1300 * 1024;
const DEPOTS_PAR_HEURE = 10;
const MARQUE = 'depot : convocation recue';

const propre = v => String(v == null ? '' : v).replace(/\s+/g, ' ').trim();

/* Le vrai type, lu dans les premiers octets. */
function typeReel(octets){
  const h = (...o) => o.every((x, i) => octets[i] === x);
  if (h(0x89, 0x50, 0x4e, 0x47)) return { mime: 'image/png', ext: 'png' };
  if (h(0xff, 0xd8, 0xff)) return { mime: 'image/jpeg', ext: 'jpg' };
  if (h(0x25, 0x50, 0x44, 0x46, 0x2d)) return { mime: 'application/pdf', ext: 'pdf' };
  if (h(0x52, 0x49, 0x46, 0x46) && octets[8] === 0x57 && octets[9] === 0x45
      && octets[10] === 0x42 && octets[11] === 0x50) return { mime: 'image/webp', ext: 'webp' };
  return null;
}

async function tropDeDepots(context){
  try {
    const r = await context.env.DB.prepare(
      "SELECT COUNT(*) AS n FROM journal WHERE loge_id = ? AND quoi = ? " +
      "AND le > datetime('now','-1 hour')").bind(LOGE, MARQUE).first();
    return Number(r?.n ?? 0) >= DEPOTS_PAR_HEURE;
  } catch (e) { return false; }
}

export async function onRequestPost(context){
  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const logeNom = propre(corps?.loge_nom).slice(0, 160);
  if (!logeNom) return json({ erreur: 'loge_manquante' }, 400);

  const b64 = String(corps?.contenu || '').replace(/^data:[^,]*,/, '').replace(/\s+/g, '');
  if (!b64 || !/^[A-Za-z0-9+/]+=*$/.test(b64)) return json({ erreur: 'fichier_illisible' }, 400);
  const taille = Math.floor(b64.length * 3 / 4) - (b64.endsWith('==') ? 2 : b64.endsWith('=') ? 1 : 0);
  if (taille > OCTETS_MAX) return json({ erreur: 'fichier_trop_lourd', max: OCTETS_MAX }, 413);

  let tete;
  try { tete = Uint8Array.from(atob(b64.slice(0, 24)), c => c.charCodeAt(0)); }
  catch (e) { return json({ erreur: 'fichier_illisible' }, 400); }
  const type = typeReel(tete);
  if (!type) return json({ erreur: 'type_refuse', accepte: ['png', 'jpg', 'webp', 'pdf'] }, 415);

  if (await tropDeDepots(context)) return json({ erreur: 'trop_de_depots' }, 429);

  const nom = (propre(corps?.nom_fichier).replace(/[\\/:*?"<>|\u0000-\u001f]/g, ' ')
    .replace(/\.[A-Za-z0-9]{1,5}$/, '').slice(0, 100) || 'convocation') + '.' + type.ext;
  try {
    await context.env.DB.prepare(
      'INSERT INTO depots_convocation (loge_id, loge_nom, nom_fichier, type_mime, octets, contenu) ' +
      'VALUES (?, ?, ?, ?, ?, ?)').bind(LOGE, logeNom, nom, type.mime, taille, b64).run();
  } catch (e) {
    return json({ erreur: 'enregistrement_impossible' }, 500);
  }
  await noter(context, LOGE, null, MARQUE);
  return json({ ok: true });
}
