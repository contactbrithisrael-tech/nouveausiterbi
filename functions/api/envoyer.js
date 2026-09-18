/* ═══════════════════════════════════════════════════════════════════
   ENVOYER LA CONVOCATION, POUR DE BON

   ► LES DESTINATAIRES NE VIENNENT PAS DE LA REQUÊTE. Ils sont lus
     dans le registre de l'Atelier, ici, sur le serveur. Une route qui
     accepterait une liste d'adresses serait un relais ouvert : il
     suffirait d'une session pour faire partir n'importe quoi vers
     n'importe qui, sous le nom de la Loge. On demande un GROUPE —
     les colonnes, les visiteurs, les Amis — et le serveur va chercher
     qui cela désigne.

   ► CHACUN SA LIGNE AU JOURNAL. Ce que le service a répondu pour
     chaque adresse est écrit. « Partie » ne veut pas dire « lue » :
     cela veut dire que le service l'a acceptée, et c'est tout ce
     qu'on peut affirmer sans mentir.

   ► SANS SERVICE CONFIGURÉ, ON LE DIT. Pas d'envoi silencieux, pas de
     faux succès : la réponse porte « configure: false », et le
     programme retombe sur la messagerie ouverte à la main.
═══════════════════════════════════════════════════════════════════ */

import { sessionCourante, json, noter } from './_commun.js';
import { remettre, fournisseur, expediteur } from './_courriel.js';

const SUJET_MAX = 300;
const CORPS_MAX = 40000;
const DESTINATAIRES_MAX = 500;

const GROUPES = ['tous', 'membres', 'visiteurs', 'amis'];

const propre = a => String(a || '').trim();
const valable = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);

function sansDoublon(liste){
  const vus = new Set(), sortie = [];
  for (const a of liste){
    const c = propre(a).toLowerCase();
    if (c && !vus.has(c)){ vus.add(c); sortie.push(propre(a)); }
  }
  return sortie;
}

/* Qui reçoit, d'après le registre — et non d'après ce qu'on nous
   demande d'envoyer.

   On rend des PERSONNES, non des adresses : il faut savoir à qui
   appartient chaque courriel pour lui remettre le lien de réponse qui
   n'est qu'à lui. Une liste d'adresses ne le permettrait pas. */
function destinataires(etat, groupe){
  const d = (etat && typeof etat === 'object') ? etat : {};
  const gens = [];
  const ajoute = (t, x, nom) => {
    if (x && x.email && valable(propre(x.email)))
      gens.push({ type: t, id: x.id, nom, email: propre(x.email) });
  };
  if (groupe === 'tous' || groupe === 'membres')
    (d.membres || []).filter(m =>
        m && !['demission','radiation','decede'].includes(m.statut))
      .forEach(m => ajoute('membre', m,
        ((m.prenoms || '') + ' ' + (m.nom || '')).trim()));
  if (groupe === 'tous' || groupe === 'visiteurs')
    (d.visiteurs || []).forEach(v => ajoute('visiteur', v,
      ((v.prenom || '') + ' ' + (v.nom || '')).trim()));
  if (groupe === 'tous' || groupe === 'amis')
    (d.amis || []).forEach(a => ajoute('ami', a,
      ((a.prenom || '') + ' ' + (a.nom || '')).trim()));

  /* Une même adresse ne reçoit qu'une fois, et c'est la première
     qualité trouvée qui la porte. */
  const vus = new Set();
  return gens.filter(g => {
    const c = g.email.toLowerCase();
    if (vus.has(c)) return false;
    vus.add(c); return true;
  });
}

/* Un jeton par personne et par tenue : trente-deux octets tirés au
   hasard, réutilisés si la convocation est renvoyée — sans quoi le
   premier lien cesserait de marcher au second envoi, et une réponse
   déjà donnée serait perdue. */
const hex = t => [...new Uint8Array(t)].map(o => o.toString(16).padStart(2, '0')).join('');

async function jetons(context, loge_id, tenue, gens){
  const dessus = new Map();
  const { results } = await context.env.DB.prepare(
    'SELECT jeton, qui_type, qui_id FROM reponses WHERE loge_id = ? AND tenue = ?')
    .bind(loge_id, tenue).all();
  for (const r of (results || [])) dessus.set(r.qui_type + ':' + r.qui_id, r.jeton);

  const neufs = [];
  for (const g of gens){
    const cle = g.type + ':' + g.id;
    if (dessus.has(cle)){ g.jeton = dessus.get(cle); continue; }
    g.jeton = hex(crypto.getRandomValues(new Uint8Array(32)));
    neufs.push(g);
  }
  if (neufs.length){
    const trous = neufs.map(() => '(?, ?, ?, ?, ?, ?, ?)').join(', ');
    const liants = [];
    for (const g of neufs)
      liants.push(g.jeton, loge_id, tenue, g.type, g.id, g.nom || '', g.email);
    try {
      await context.env.DB.prepare(
        'INSERT INTO reponses (jeton, loge_id, tenue, qui_type, qui_id, nom, courriel) ' +
        'VALUES ' + trous).bind(...liants).run();
    } catch (e) { /* une ligne déjà là : le lien existant fera l'affaire */ }
  }
  return gens;
}

export async function onRequestPost(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  let corpsRequete;
  try { corpsRequete = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const groupe = GROUPES.includes(corpsRequete?.groupe) ? corpsRequete.groupe : null;
  const sujet  = propre(corpsRequete?.sujet);
  const corps  = typeof corpsRequete?.corps === 'string' ? corpsRequete.corps : '';

  if (!groupe) return json({ erreur: 'groupe_inconnu', groupes: GROUPES }, 400);
  if (!sujet)  return json({ erreur: 'sujet_manquant' }, 400);
  if (!corps.trim()) return json({ erreur: 'corps_manquant' }, 400);
  if (sujet.length > SUJET_MAX) return json({ erreur: 'sujet_trop_long' }, 400);
  if (corps.length > CORPS_MAX) return json({ erreur: 'corps_trop_long' }, 413);

  /* Le service est-il là ? On le dit AVANT de lire quoi que ce soit :
     inutile de faire travailler la base pour rien. */
  if (!fournisseur(context.env) || !expediteur(context.env).adresse)
    return json({ configure: false,
      pourquoi: !fournisseur(context.env) ? 'aucune_cle' : 'expediteur_manquant' });

  const r = await context.env.DB.prepare(
    'SELECT donnees FROM etat WHERE loge_id = ?').bind(moi.loge_id).first();
  let etat = null;
  try { etat = r ? JSON.parse(r.donnees) : null; }
  catch (e) { return json({ erreur: 'etat_illisible' }, 500); }

  const gens = destinataires(etat, groupe);
  if (!gens.length) return json({ erreur: 'aucun_destinataire', groupe }, 400);
  if (gens.length > DESTINATAIRES_MAX)
    return json({ erreur: 'trop_de_destinataires', combien: gens.length }, 413);

  /* ── LE LIEN DE RÉPONSE ──────────────────────────────────────────
     Demandé seulement quand le message en appelle une — une
     convocation, non une lettre de nouvelles. Chacun reçoit LE SIEN :
     c'est ce qui permet de compter les présents et les couverts sans
     que personne ne dépouille quatre-vingts courriels à la main. */
  const veutReponse = corpsRequete?.reponse === true;
  const tenue = propre(corpsRequete?.tenue) ||
                (etat && etat.tenue && etat.tenue.date) || '';
  let avecJeton = gens;
  if (veutReponse && tenue)
    avecJeton = await jetons(context, moi.loge_id, tenue, gens);

  const racine = new URL(context.request.url).origin;
  const corpsPour = g => (veutReponse && g.jeton)
    ? corps + '\n\n' +
      '— — — — — — — — — — — — — — — — — — — —\n' +
      'RÉPONDEZ D\'UN CLIC — ce lien n\'est qu\'à vous :\n' +
      racine + '/reponse.html?j=' + g.jeton + '\n' +
      'Présent ou excusé, et si vous restez aux agapes.\n' +
      'Votre réponse est comptée aussitôt ; le traiteur en dépend.'
    : corps;

  const liste = gens.map(g => g.email);
  const sortie = await remettre(context.env, sujet, corpsPour, gens);
  if (!sortie.configure)
    return json({ configure: false, pourquoi: sortie.pourquoi || 'aucune_cle' });

  /* Le journal, une ligne par personne. On l'écrit en un seul lot :
     quatre-vingts écritures séparées coûteraient plus que l'envoi. */
  const valeurs = [], liants = [];
  for (const x of sortie.resultats){
    valeurs.push('(?, ?, ?, ?, ?, ?, ?)');
    liants.push(moi.loge_id, moi.id, sujet, groupe, x.adresse, x.statut, x.detail || null);
  }
  try {
    await context.env.DB.prepare(
      'INSERT INTO envois (loge_id, par, sujet, groupe, destinataire, statut, detail) ' +
      'VALUES ' + valeurs.join(', ')).bind(...liants).run();
  } catch (e) { /* le journal ne doit pas faire échouer l'envoi qu'il consigne */ }

  const parties = sortie.resultats.filter(x => x.statut === 'partie').length;
  const refusees = sortie.resultats.filter(x => x.statut !== 'partie');

  await noter(context, moi.loge_id, moi.id,
    `convocation remise à ${parties} destinataire(s)` +
    (refusees.length ? `, ${refusees.length} refusée(s)` : ''));

  return json({ configure: true, service: sortie.service,
                demandes: liste.length, parties,
                refusees: refusees.map(x => ({ adresse: x.adresse, detail: x.detail })) });
}

/* Ce que l'écran a besoin de savoir avant de proposer le bouton. */
export async function onRequestGet(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);
  const f = fournisseur(context.env), de = expediteur(context.env);
  return json({ configure: !!f && !!de.adresse,
                service: f ? f.nom : null,
                expediteur: de.adresse || null,
                reponse: de.reponse || null });
}
