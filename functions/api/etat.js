/* ═══════════════════════════════════════════════════════════════════
   L'ÉTAT DE L'ATELIER, PARTAGÉ

   C'est ce qui règle le vrai problème : jusqu'ici la Sœur Secrétaire
   et le Trésorier travaillaient chacun dans son navigateur, et se
   passaient un fichier. Le premier qui rechargeait le fichier de
   l'autre effaçait son propre travail, sans que rien ne l'en avertisse.

   ► LA VERSION EST LA GARDE. Chaque écriture annonce la version sur
     laquelle elle se fonde. Si quelqu'un a écrit entre-temps, le
     serveur REFUSE (409) et rend l'état à jour : celui qui écrivait
     voit ce qu'il allait écraser, au lieu de l'apprendre trop tard.

     L'UPDATE porte lui-même la condition « AND version = ? ». Vérifier
     d'abord puis écrire laisserait passer deux écritures simultanées :
     c'est la base qui doit trancher, en une seule opération.

   ► LE JOURNAL garde qui a écrit et quand. Une comptabilité sans trace
     de ses écritures ne se vérifie pas.

   ► RIEN N'EST SERVI SANS SESSION. Pas de session : 401, et pas un mot
     de plus.
═══════════════════════════════════════════════════════════════════ */

import { sessionCourante, json, noter } from './_commun.js';
import { fusionner } from './_fusion.js';

const POIDS_MAX = 4 * 1024 * 1024;   // 4 Mio : large pour un Atelier

export async function onRequestGet(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  const r = await context.env.DB.prepare(
    'SELECT donnees, version, modifie_le FROM etat WHERE loge_id = ?')
    .bind(moi.loge_id).first();

  /* Aucun état encore : ce n'est pas une erreur, c'est un Atelier qui
     n'a pas encore été saisi. Version 0 vaut « rien n'a été écrit ». */
  if (!r) return json({ donnees: null, version: 0,
                        qui: moi.nom, charge: moi.charge });

  let donnees = null;
  try { donnees = JSON.parse(r.donnees); }
  catch (e) { return json({ erreur: 'etat_illisible', version: r.version }, 500); }

  return json({ donnees, version: r.version, modifie_le: r.modifie_le,
                qui: moi.nom, charge: moi.charge });
}

export async function onRequestPut(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  if (!corps || typeof corps.donnees !== 'object' || corps.donnees === null)
    return json({ erreur: 'donnees_manquantes' }, 400);
  if (!Number.isInteger(corps.version) || corps.version < 0)
    return json({ erreur: 'version_manquante' }, 400);

  const texte = JSON.stringify(corps.donnees);
  if (texte.length > POIDS_MAX)
    return json({ erreur: 'trop_gros', poids: texte.length }, 413);

  /* Première écriture : personne n'a encore rien posé. INSERT échoue
     de lui-même si un autre l'a devancée entre-temps. */
  if (corps.version === 0){
    try {
      await context.env.DB.prepare(
        'INSERT INTO etat (loge_id, donnees, version, modifie_par) VALUES (?, ?, 1, ?)')
        .bind(moi.loge_id, texte, moi.id).run();
      await noter(context, moi.loge_id, moi.id, 'premier enregistrement');
      return json({ version: 1 });
    } catch (e) {
      const a = await context.env.DB.prepare(
        'SELECT donnees, version, modifie_le FROM etat WHERE loge_id = ?')
        .bind(moi.loge_id).first();
      return conflit(a);
    }
  }

  const res = await context.env.DB.prepare(
    `UPDATE etat SET donnees = ?, version = version + 1,
            modifie_le = datetime('now'), modifie_par = ?
      WHERE loge_id = ? AND version = ?`)
    .bind(texte, moi.id, moi.loge_id, corps.version).run();

  if (res?.meta?.changes ?? res?.changes ?? 0){
    await noter(context, moi.loge_id, moi.id, 'enregistrement');
    return json({ version: corps.version + 1 });
  }

  /* ── QUELQU'UN A ÉCRIT ENTRE-TEMPS ────────────────────────────────
     On refusait ici, et le programme posait la question qui perd du
     travail : « OK, je reprends la version du registre — ce qui n'est
     que sur cet appareil sera perdu. » À deux, l'un des deux
     recommençait. C'était la conséquence d'écrire en bloc, et cela
     rendait impossible le travail à plusieurs — qui était pourtant la
     raison d'être de ce serveur.

     On fusionne désormais, quand le programme a renvoyé son SOCLE : le
     document tel qu'il était quand celui qui écrit a commencé. Avec
     lui on sait qui a changé quoi, et les deux travaux tiennent.

     ► ON REFAIT LE TOUR À CHAQUE FOIS. Entre la relecture et
       l'écriture, un troisième peut encore passer : la condition
       « AND version = ? » le rattrape, et l'on recommence sur l'état
       qu'il a laissé. Trois tours suffisent largement pour un Atelier
       de treize personnes ; au-delà, on refuse plutôt que de tourner.

     ► SANS SOCLE, L'ANCIEN REFUS. Un programme d'une version
       précédente n'en envoie pas : il doit continuer de recevoir ce
       qu'il sait traiter, et non une réponse qu'il prendrait pour un
       succès. */
  const avecSocle = corps.socle !== null && typeof corps.socle === 'object';
  for (let tour = 0; avecSocle && tour < 3; tour++){
    const a = await context.env.DB.prepare(
      'SELECT donnees, version, modifie_le FROM etat WHERE loge_id = ?')
      .bind(moi.loge_id).first();
    if (!a) break;
    let leur;
    try { leur = JSON.parse(a.donnees); } catch (e) { break; }

    const ecrases = [];
    const fondu = fusionner(corps.socle, leur, corps.donnees, ecrases);
    const fonduTexte = JSON.stringify(fondu);
    if (fonduTexte.length > POIDS_MAX)
      return json({ erreur: 'trop_gros', poids: fonduTexte.length }, 413);

    const r2 = await context.env.DB.prepare(
      `UPDATE etat SET donnees = ?, version = version + 1,
              modifie_le = datetime('now'), modifie_par = ?
        WHERE loge_id = ? AND version = ?`)
      .bind(fonduTexte, moi.id, moi.loge_id, a.version).run();
    if (!(r2?.meta?.changes ?? r2?.changes ?? 0)) continue;   // un troisième est passé

    await noter(context, moi.loge_id, moi.id,
      'enregistrement fusionné avec celui du registre' +
      (ecrases.length ? ' — tranché sur : ' + ecrases.slice(0, 20).join(', ') : ''));
    /* On rend le document fusionné : celui qui écrit doit voir
       apparaître le travail de l'autre, sans recharger et sans qu'on
       lui demande de choisir. */
    return json({ version: a.version + 1, donnees: fondu,
                  fusion: { depuis: corps.version, ecrases } });
  }

  const a = await context.env.DB.prepare(
    'SELECT donnees, version, modifie_le FROM etat WHERE loge_id = ?')
    .bind(moi.loge_id).first();
  await noter(context, moi.loge_id, moi.id, 'écriture refusée : version périmée');
  return conflit(a);
}

/* On rend l'état à jour AVEC le refus : sans lui, celui qui écrivait
   n'aurait qu'un message d'erreur et son travail sur les bras. */
function conflit(actuel){
  let donnees = null;
  try { donnees = actuel ? JSON.parse(actuel.donnees) : null; } catch (e) {}
  return json({ erreur: 'conflit', version: actuel?.version ?? 0,
                modifie_le: actuel?.modifie_le ?? null, donnees }, 409);
}
