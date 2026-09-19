/* ═══════════════════════════════════════════════════════════════════
   L'ANNUAIRE — DÉPOSER, ET RELEVER

   POST — sans session. C'est le formulaire de l'Espace Membres qui
   écrit ici, et il écrit depuis le navigateur d'un Frère, pas depuis
   une session d'Officier.

   Cette route est atteignable sans jamais charger la page : le
   tuilage garde le seuil de l'Espace Membres, il ne garde pas une
   adresse HTTP. Ce qui arrive ici est donc traité comme ce que c'est
   — une déclaration, pas une identité établie. On la borne, on la
   range dans sa propre table, et le carnet des Visiteurs la recevra
   avec sa case « Tuilé par » VIDE : le Rite a déjà prévu qui répond
   de l'introduction d'un Visiteur dans le Temple, et ce n'est pas un
   formulaire.

   GET — avec session. Rend les fiches qui n'ont pas encore rejoint le
   carnet, et le compte de celles qui y sont déjà.

   PUT — avec session. Marque comme versées celles dont on donne les
   numéros. Rien n'est effacé : une fiche reçue est une trace.
═══════════════════════════════════════════════════════════════════ */

import { sessionCourante, json, noter } from './_commun.js';

const LOGE = 1;                    // un seul Atelier pour l'instant
const POIDS_MAX = 8 * 1024;        // une fiche, pas un fichier
const EN_ATTENTE_MAX = 300;        // au-delà, on cesse d'accepter
const CHAMP_MAX = 400;

/* Les seuls champs retenus. Ce qui n'est pas dans cette liste est
   jeté : un formulaire public ne décide pas de ce que porte la base. */
const CHAMPS = ['prenom','nom','email','telephone','ville','pays','grade',
                'loge','obedience','rite','dispo_notes','jours','souhaits',
                'accord_partage'];

/* ── UNE LOGE N'EST PAS UNE PERSONNE ────────────────────────────────
   Un Atelier qui souhaite recevoir nos convocations n'inscrit pas un
   Frère : il inscrit SA SECRÉTAIRE ou SON SECRÉTAIRE, à qui les
   convocations seront adressées, et il dépose son propre état civil —
   nom, numéro, orient, obédience, rite, temple.

   Ce n'est donc pas la même fiche, et il serait faux de la ranger avec
   les Visiteurs : une Loge ne visite pas, elle correspond. Elle rejoint
   le carnet des LOGES AMIES.

   Deux formulaires, deux jeux de champs, une seule route : c'est le
   champ « type » qui décide, et rien d'autre. */
const CHAMPS_LOGE = ['loge_nom','loge_numero','loge_orient','loge_obedience',
                     'loge_rite','loge_temple','loge_adresse','loge_cp',
                     'loge_ville','contact_nom','contact_email','contact_tel',
                     'loge_notes'];

/* ── ET LA CONVOCATION QU'ELLE DÉPOSE ───────────────────────────────
   Un Atelier qui nous invite dépose ce qui se met à l'agenda : une
   date, une heure, un degré, un objet. Le feuillet lui-même reste
   CHEZ LUI — on n'en garde qu'un lien, s'il en a un en ligne.

   C'est un choix, et il se dit : porter les fichiers des autres, ce
   serait s'engager à les garder, à les servir, et à répondre de ce
   qu'ils contiennent. Un lien n'engage à rien de tout cela, et il
   mène au même feuillet. */
const CHAMPS_CONV = ['loge_nom','loge_numero','contact_email',
                     'conv_date','conv_heure','conv_degre','conv_objet',
                     'conv_lieu','conv_odj','conv_lien'];

/* Une date au format du calendrier, non un texte libre : c'est elle
   qui range la Tenue à l'agenda, et une date qu'on ne sait pas lire
   ne se range nulle part. */
const dateLisible = d => /^\d{4}-\d{2}-\d{2}$/.test(d);

/* Un lien vers un feuillet, et rien d'autre : ni « javascript: », ni
   une adresse qu'on nous ferait ouvrir. */
const lienSur = u => /^https:\/\/[^\s"'<>]+$/.test(u);

const texte = v => {
  if (Array.isArray(v)) v = v.join(', ');
  if (typeof v === 'boolean') return v ? 'oui' : '';
  if (v === null || v === undefined) return '';
  return String(v).replace(/\s+/g, ' ').trim().slice(0, CHAMP_MAX);
};

/* Un courriel reconnaissable, sans prétendre valider ce qui ne se
   valide qu'en écrivant à l'adresse. */
const courrielPlausible = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);

export async function onRequestPost(context){
  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  if (!corps || typeof corps !== 'object')
    return json({ erreur: 'requete_illisible' }, 400);

  const quoi = texte(corps.type);
  const estLoge = quoi === 'loge';
  const estConv = quoi === 'convocation';
  const fiche = {};
  for (const c of (estConv ? CHAMPS_CONV : estLoge ? CHAMPS_LOGE : CHAMPS)){
    const v = texte(corps[c]); if (v) fiche[c] = v;
  }
  if (estLoge) fiche.type = 'loge';
  if (estConv) fiche.type = 'convocation';

  if (estConv){
    /* De quelle Loge, et quel jour. Sans l'un on ne sait à qui
       rattacher la Tenue ; sans l'autre elle ne se range nulle part. */
    if (!fiche.loge_nom && !fiche.contact_email)
      return json({ erreur: 'loge_manquante' }, 400);
    if (!dateLisible(fiche.conv_date || ''))
      return json({ erreur: 'date_manquante' }, 400);
    /* Un lien qu'on ne peut pas suivre vaut mieux retiré qu'affiché :
       on le laisse tomber plutôt que de poser un bouton mort. */
    if (fiche.conv_lien && !lienSur(fiche.conv_lien)) delete fiche.conv_lien;
  } else if (estLoge){
    /* Le nom de l'Atelier, et une adresse où lui écrire. Sans l'un,
       on ne sait pas qui inscrit ; sans l'autre, on ne peut pas lui
       envoyer ce qu'il est venu demander. */
    if (!fiche.loge_nom) return json({ erreur: 'loge_manquante' }, 400);
    if (!fiche.contact_email || !courrielPlausible(fiche.contact_email))
      return json({ erreur: 'courriel_manquant' }, 400);
  } else {
    /* De quoi savoir de qui il s'agit et comment le joindre. Sans cela,
       la fiche n'apprend rien et n'encombre que la base. */
    if (!fiche.nom || !fiche.prenom) return json({ erreur: 'nom_manquant' }, 400);
    if (!fiche.email || !courrielPlausible(fiche.email))
      return json({ erreur: 'courriel_manquant' }, 400);
  }

  const brut = JSON.stringify(fiche);
  if (brut.length > POIDS_MAX) return json({ erreur: 'trop_gros' }, 413);

  /* Une file qui n'a pas été relevée depuis longtemps ne doit pas
     pouvoir être gonflée sans fin. On refuse, et on le dit : le
     formulaire retombe alors sur le courriel, qui arrive toujours. */
  const attente = await context.env.DB.prepare(
    'SELECT COUNT(*) AS n FROM annuaire WHERE loge_id = ? AND versee = 0')
    .bind(LOGE).first();
  if (Number(attente?.n ?? 0) >= EN_ATTENTE_MAX)
    return json({ erreur: 'file_pleine' }, 429);

  await context.env.DB.prepare(
    'INSERT INTO annuaire (loge_id, source, donnees) VALUES (?, ?, ?)')
    .bind(LOGE, texte(corps.source) || 'espace-membres', brut).run();

  await noter(context, LOGE, null, 'fiche reçue de l’annuaire');
  return json({ recue: true });
}

export async function onRequestGet(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  /* ── L'ANNUAIRE DU SITE ARRIVE-T-IL SEULEMENT ? ───────────────────
     La liste ci-dessous ne rend que les fiches EN ATTENTE. Elle est
     donc vide dans deux cas qu'on ne peut pas distinguer : tout a été
     versé au carnet — ou rien n'est jamais arrivé.

     Et rien n'arriverait sans bruit : le formulaire de l'Espace
     Membres dépose sa fiche « au cas où », et avale l'échec
     volontairement, parce que le courriel, lui, part de toute façon.
     Ce choix protège le Frère qui remplit le formulaire ; il aveugle
     la Secrétaire, qui est la seule à pouvoir y remédier.

     Ce compte la rend voyante. Des NOMBRES seuls, et la date de la
     dernière fiche reçue : ni nom, ni adresse. */
  if (new URL(context.request.url).searchParams.get('compte') === '1'){
    try {
      const r = await context.env.DB.prepare(
        'SELECT COUNT(*) AS recues, ' +
        'SUM(CASE WHEN versee = 0 THEN 1 ELSE 0 END) AS attente, ' +
        'MAX(recu_le) AS derniere FROM annuaire WHERE loge_id = ?')
        .bind(moi.loge_id).first();
      const recues = Number(r?.recues || 0);
      const attente = Number(r?.attente || 0);
      return json({ compte: {
        recues, attente, versees: recues - attente,
        derniere: r?.derniere || null } });
    } catch (e) {
      return json({ erreur: 'annuaire_illisible',
        detail: 'La table de l’annuaire n’a pas pu être lue. ' +
                'Vérifiez que 002-annuaire.sql a été joué sur la base.' }, 500);
    }
  }

  const { results } = await context.env.DB.prepare(
    'SELECT id, recu_le, source, donnees FROM annuaire ' +
    'WHERE loge_id = ? AND versee = 0 ORDER BY id').bind(moi.loge_id).all();

  const fiches = [];
  for (const r of (results || [])){
    let d = null;
    try { d = JSON.parse(r.donnees); } catch (e) { continue; }  // illisible : on passe
    fiches.push({ id: r.id, recu_le: r.recu_le, source: r.source, fiche: d });
  }
  return json({ fiches });
}

export async function onRequestPut(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const ids = Array.isArray(corps?.versees)
    ? corps.versees.filter(Number.isInteger).slice(0, 500) : [];
  if (!ids.length) return json({ versees: 0 });

  const trous = ids.map(() => '?').join(',');
  const r = await context.env.DB.prepare(
    `UPDATE annuaire SET versee = 1, versee_le = datetime('now')
      WHERE loge_id = ? AND versee = 0 AND id IN (${trous})`)
    .bind(moi.loge_id, ...ids).run();

  const n = r?.meta?.changes ?? 0;
  if (n) await noter(context, moi.loge_id, moi.id,
                     n + ' fiche(s) de l’annuaire versée(s) au carnet');
  return json({ versees: n });
}
