/* ═══════════════════════════════════════════════════════════════════
   LES CONVOCATIONS DÉPOSÉES, VUES PAR LE SECRÉTARIAT

   Les Loges amies déposent (route « depot »). Ici, une session de
   l'Atelier les liste, regarde l'image, VALIDE ou REFUSE, puis envoie
   la convocation validée à tous les membres, en un clic.

   ► RIEN NE PART SANS RELECTURE. La liste porte un brouillon de
     courriel ; l'écran le montre, on peut le changer, et c'est ce
     texte-là qui part. Il n'ajoute rien à ce que la Loge a déposé.
   ► UN ENVOI, UNE FOIS. Seul un dépôt « validé » part, et il passe à
     « envoyé » : un second clic ne renvoie rien.
   ► LES DESTINATAIRES NE VIENNENT PAS DE LA REQUÊTE : ils sont lus au
     registre, les membres seuls (ni démissionnaires, ni radiés, ni
     décédés), comme pour la convocation de la Tenue.
═══════════════════════════════════════════════════════════════════ */

import { sessionCourante, json, noter } from './_commun.js';
import { remettre, fournisseur, expediteur } from './_courriel.js';

const ACTIONS = ['valider', 'refuser', 'envoyer'];
const SUJET_MAX = 300, CORPS_MAX = 20000;
const propre = v => String(v == null ? '' : v).trim();
const valable = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);

const brouillon = d => ({
  sujet: 'Visite : convocation de la Loge ' + d.loge_nom,
  corps: 'Mes très chères Sœurs, mes très chers Frères,\n\n' +
    'La Loge ' + d.loge_nom + ' nous fait parvenir sa convocation, que vous trouverez en pièce jointe.\n\n' +
    'Le Secrétariat'
});

function membres(etat){
  const vus = new Set(), gens = [];
  for (const m of ((etat && etat.membres) || [])){
    if (!m || ['demission', 'radiation', 'decede'].includes(m.statut)) continue;
    const e = propre(m.email), c = e.toLowerCase();
    if (!valable(e) || vus.has(c)) continue;
    vus.add(c);
    gens.push({ email: e, nom: ((m.prenoms || '') + ' ' + (m.nom || '')).trim() });
  }
  return gens;
}

export async function onRequestGet(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);
  const db = context.env.DB;
  const id = Number(new URL(context.request.url).searchParams.get('id'));
  try {
    if (id){                                   // l'image elle-même, pour l'écran
      const d = await db.prepare('SELECT type_mime, contenu FROM depots_convocation ' +
        'WHERE id = ? AND loge_id = ?').bind(id, moi.loge_id).first();
      if (!d) return json({ erreur: 'introuvable' }, 404);
      const bin = Uint8Array.from(atob(d.contenu), c => c.charCodeAt(0));
      return new Response(bin, { headers: { 'content-type': d.type_mime,
        'content-disposition': 'inline', 'x-content-type-options': 'nosniff',
        'cache-control': 'private, no-store' } });
    }
    const { results } = await db.prepare(
      'SELECT id, le, loge_nom, nom_fichier, type_mime, octets, statut, envoye_le, nb_envoyes ' +
      'FROM depots_convocation WHERE loge_id = ? ORDER BY (statut = \'attente\') DESC, le DESC LIMIT 100')
      .bind(moi.loge_id).all();
    return json({ depots: (results || []).map(d => ({ ...d, brouillon: brouillon(d) })) });
  } catch (e) { return json({ depots: [] }); }  // la table n'existe pas encore : rien à montrer
}

export async function onRequestPost(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);
  let c; try { c = await context.request.json(); } catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  const id = Number(c?.id), action = c?.action;
  if (!id || !ACTIONS.includes(action)) return json({ erreur: 'demande_inconnue' }, 400);
  const db = context.env.DB;
  const d = await db.prepare('SELECT id, loge_nom, nom_fichier, contenu, statut FROM depots_convocation ' +
    'WHERE id = ? AND loge_id = ?').bind(id, moi.loge_id).first();
  if (!d) return json({ erreur: 'introuvable' }, 404);

  if (action !== 'envoyer'){
    const neuf = action === 'valider' ? 'validee' : 'refusee';
    if (d.statut === 'envoyee') return json({ erreur: 'deja_envoye' }, 409);
    await db.prepare("UPDATE depots_convocation SET statut = ?, decide_par = ?, decide_le = datetime('now') WHERE id = ?")
      .bind(neuf, moi.id, id).run();
    await noter(context, moi.loge_id, moi.id, 'depot ' + id + ' ' + neuf);
    return json({ ok: true, statut: neuf });
  }

  if (d.statut !== 'validee') return json({ erreur: d.statut === 'envoyee' ? 'deja_envoye' : 'pas_valide' }, 409);
  const sujet = propre(c.sujet), corps = typeof c.corps === 'string' ? c.corps : '';
  if (!sujet || !corps.trim()) return json({ erreur: 'texte_manquant' }, 400);
  if (sujet.length > SUJET_MAX || corps.length > CORPS_MAX) return json({ erreur: 'texte_trop_long' }, 413);
  if (!fournisseur(context.env) || !expediteur(context.env).adresse) return json({ configure: false });

  const r = await db.prepare('SELECT donnees FROM etat WHERE loge_id = ?').bind(moi.loge_id).first();
  let etat = null; try { etat = r ? JSON.parse(r.donnees) : null; } catch (e) { return json({ erreur: 'etat_illisible' }, 500); }
  const gens = membres(etat);
  if (!gens.length) return json({ erreur: 'aucun_destinataire' }, 400);

  const sortie = await remettre(context.env, sujet, corps, gens, { nom: d.nom_fichier, contenu: d.contenu });
  if (!sortie.configure) return json({ configure: false });
  const parties = sortie.resultats.filter(x => x.statut === 'partie').length;
  if (parties){                                // au moins un envoi : le dépôt est « envoyé », pas plus
    await db.prepare("UPDATE depots_convocation SET statut = 'envoyee', envoye_le = datetime('now'), nb_envoyes = ? WHERE id = ?")
      .bind(parties, id).run();
  }
  await noter(context, moi.loge_id, moi.id, 'depot ' + id + ' envoye a ' + parties + ' membre(s)');
  return json({ configure: true, demandes: gens.length, parties,
    refusees: sortie.resultats.filter(x => x.statut !== 'partie').map(x => ({ adresse: x.adresse, detail: x.detail })) });
}
