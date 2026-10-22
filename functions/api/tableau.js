/* ═══════════════════════════════════════════════════════════════════
   LE TABLEAU DE LA LOGE, VU PAR UNE COLONNE

   Demandé : un onglet qui porte les noms des Sœurs et Frères inscrits
   au Tableau, avec présent, absent, agapes — et où chacun puisse se
   déclarer lui-même.

   ── CE QUI GARDE CETTE PORTE, ET CE QUE CELA VAUT ─────────────────

   Deux choses, et il faut dire ce que chacune fait :

   ► LE TUILAGE DE L'ESPACE MEMBRES écarte le passant et le moteur
     d'indexation. Il n'écarte pas qui lit le code source de la page :
     les réponses attendues y sont écrites en clair. Seul, il ne
     protège donc RIEN.

   ► LE COURRIEL DU MEMBRE est le vrai filtre. Nul ne voit le Tableau
     sans donner une adresse qui figure parmi les convoqués. Une
     adresse n'est pas un secret — mais ce n'est pas non plus une
     donnée publique, et il faut la connaître pour entrer.

   Dit autrement : qui connaît l'adresse d'une Sœur de l'Atelier peut
   voir le Tableau. Ce n'est pas un coffre, c'est une porte avec un
   nom dessus. C'est l'arbitrage retenu, en connaissance de cause, et
   il vaut mieux que la liste en accès libre.

   ── CE QUI SORT D'ICI, ET RIEN DE PLUS ────────────────────────────

   Le nom, la réponse, les agapes. PAS les adresses des autres, pas
   les téléphones, pas la trésorerie, pas les jetons, pas le registre.
   Une adresse retrouvée dans une boîte aux lettres ne doit pas ouvrir
   le registre de l'Atelier.

   ── ON N'INVENTE AUCUN STOCKAGE ───────────────────────────────────

   La table « reponses » porte déjà, pour chaque convoqué, son nom, son
   courriel, sa réponse et ses agapes : elle est écrite au moment où
   les convocations partent. C'est donc elle qu'on lit, et elle qu'on
   écrit — la même ligne que le lien personnel de la convocation.

   Conséquence qui compte : le programme de la Secrétaire relève déjà
   cette table. Ce qu'une colonne déclare ici lui arrive par le chemin
   qui existe, sans nouvelle fusion et sans conflit de version.
═══════════════════════════════════════════════════════════════════ */

import { json, noter } from './_commun.js';

const LOGE = 1;                      // un seul Atelier pour l'instant
const REPONSES = ['present', 'excuse'];
const ESSAIS_MAX = 30;               // adresses essayées par heure
const MARQUE = 'tableau : adresse inconnue';

const courrielPlausible = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);

const propre = v => String(v == null ? '' : v)
  .replace(/\s+/g, ' ').trim().slice(0, 200);

/* La tenue en cours : la plus récente pour laquelle des convocations
   sont parties. Les dates sont en ISO, l'ordre des caractères est donc
   l'ordre du calendrier. */
async function tenueCourante(context){
  const r = await context.env.DB.prepare(
    'SELECT MAX(tenue) AS t FROM reponses WHERE loge_id = ?').bind(LOGE).first();
  return r?.t || null;
}

/* ── CONTRE L'ESSAI D'ADRESSES AU HASARD ───────────────────────────
   Sans borne, on pourrait présenter des adresses l'une après l'autre
   jusqu'à en trouver une qui ouvre. Les échecs sont comptés, et
   au-delà de trente par heure on cesse de répondre — pour tout le
   monde, une heure durant, puis cela se rouvre tout seul.

   Ce que cela ne fait pas : arrêter quelqu'un qui connaît DÉJÀ une
   adresse. Rien ici ne le peut, et c'est l'arbitrage assumé plus haut. */
async function tropDEssais(context){
  try {
    const r = await context.env.DB.prepare(
      "SELECT COUNT(*) AS n FROM journal WHERE loge_id = ? AND quoi = ? " +
      "AND le > datetime('now','-1 hour')").bind(LOGE, MARQUE).first();
    return Number(r?.n ?? 0) >= ESSAIS_MAX;
  } catch (e) { return false; }
}

/* La ligne de celui qui se présente. On cherche sur le courriel, sans
   tenir compte de la casse : une adresse écrite avec une majuscule est
   la même adresse. */
async function maLigne(context, tenue, courriel){
  return await context.env.DB.prepare(
    "SELECT jeton, qui_id, nom, reponse, agapes FROM reponses " +
    "WHERE loge_id = ? AND tenue = ? AND qui_type = 'membre' " +
    "AND lower(trim(courriel)) = ?")
    .bind(LOGE, tenue, courriel).first();
}

/* Le Tableau tel qu'il s'affiche. Les MEMBRES seuls : c'est ce qui a
   été demandé, et les Visiteurs ont leur propre feuille. On rend le
   nom, la réponse et les agapes — jamais le courriel d'un autre, et
   jamais un jeton. */
async function leTableau(context, tenue){
  const { results } = await context.env.DB.prepare(
    "SELECT qui_id, nom, reponse, agapes FROM reponses " +
    "WHERE loge_id = ? AND tenue = ? AND qui_type = 'membre' " +
    "ORDER BY qui_id").bind(LOGE, tenue).all();
  return (results || []).map(r => ({
    id: r.qui_id,
    nom: r.nom || '',
    reponse: r.reponse || null,
    agapes: r.agapes === null || r.agapes === undefined ? null : !!r.agapes
  }));
}

/* ── LA DATE DE LA PROCHAINE TENUE, ET RIEN D'AUTRE ────────────────
   Le formulaire « Annoncer ma venue » portait sa date ÉCRITE EN DUR :
   <input type="hidden" name="tenue_date" value="2026-11-02">. Deux
   conséquences, et la seconde est la mauvaise :

   — il faut la changer à la main à chaque Tenue, et le jour où on
     l'oublie les Visiteurs s'annoncent pour une date passée, sans que
     rien ne le signale ;
   — le Visiteur ne voyait pas pour quelle Tenue il s'engageait. Un
     champ caché fait signer sans lire.

   Cette route rend la date, et strictement elle. Pas le lieu, pas
   l'heure, pas le titre, pas l'ordre du jour, pas un nom : une Tenue
   a une date, et c'est tout ce dont un formulaire d'annonce a besoin.

   ► CE QU'ON DIVULGUE ICI, ET POURQUOI C'EST ACCEPTÉ. Sans session :
     n'importe qui peut demander cette date. Elle figure déjà sur les
     convocations qui circulent entre Ateliers, et la page qui invite
     les Visiteurs à s'annoncer doit bien la leur dire. Divulguer le
     lieu serait un autre arbitrage — il n'est pas pris ici.

   ► ELLE SORT DU REGISTRE, non de la table des réponses : le registre
     la porte dès que la Secrétaire l'a saisie, alors que les réponses
     n'existent qu'une fois les convocations parties. Un Visiteur doit
     pouvoir s'annoncer AVANT que les convocations ne partent. */
export async function onRequestGet(context){
  try {
    const r = await context.env.DB.prepare(
      'SELECT donnees FROM etat WHERE loge_id = ?').bind(LOGE).first();
    if (!r) return json({ tenue: null });
    const d = JSON.parse(r.donnees)?.tenue?.date;
    /* Une date au format du calendrier, ou rien : on ne rend pas un
       texte libre que la page irait poser dans un champ « date ». */
    return json({ tenue: /^\d{4}-\d{2}-\d{2}$/.test(d) ? d : null });
  } catch (e) {
    /* Le registre illisible n'est pas une raison de rendre une erreur
       parlante à qui n'a pas de session : on rend « pas de date », et
       le formulaire laisse le Visiteur la saisir. */
    return json({ tenue: null });
  }
}

/* ── SE PRÉSENTER ──────────────────────────────────────────────────
   POST { courriel } rend le Tableau, et la ligne de celui qui demande.

   Une seule et même réponse pour une adresse inconnue et pour un
   Atelier qui n'a pas encore convoqué : ce qui sort d'ici ne doit pas
   permettre de deviner qui est au Tableau. */
export async function onRequestPost(context){
  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  if (!corps || typeof corps !== 'object')
    return json({ erreur: 'requete_illisible' }, 400);

  const courriel = propre(corps.courriel).toLowerCase();
  if (!courrielPlausible(courriel))
    return json({ erreur: 'courriel_manquant' }, 400);

  if (await tropDEssais(context))
    return json({ erreur: 'trop_dessais' }, 429);

  const tenue = await tenueCourante(context);
  if (!tenue){
    /* Aucune convocation n'est encore partie : il n'y a pas de Tableau
       à montrer, et ce n'est pas une panne. On le dit tel quel — c'est
       la Secrétaire qui convoque, non cette page. */
    return json({ erreur: 'aucune_convocation' }, 404);
  }

  const moi = await maLigne(context, tenue, courriel);
  if (!moi){
    await noter(context, LOGE, null, MARQUE);
    return json({ erreur: 'inconnu' }, 404);
  }

  /* On répond à une demande d'écriture dans la foulée, s'il y en a
     une : se déclarer en arrivant évite un second aller-retour. */
  let ecrit = null;
  if (corps.reponse !== undefined || corps.agapes !== undefined)
    ecrit = await enregistrer(context, moi.jeton, corps);
  if (ecrit && ecrit.erreur) return json(ecrit, 400);

  const apres = ecrit ? await maLigne(context, tenue, courriel) : moi;

  return json({
    tenue,
    moi: { id: apres.qui_id, nom: apres.nom || '',
           reponse: apres.reponse || null,
           agapes: apres.agapes === null || apres.agapes === undefined
                   ? null : !!apres.agapes },
    tableau: await leTableau(context, tenue)
  });
}

/* ── CE QU'UNE COLONNE DÉCLARE POUR ELLE-MÊME ──────────────────────
   On n'écrit que SA ligne, désignée par le jeton qu'on vient de
   retrouver à partir de son adresse. Rien ne permet d'écrire celle
   d'un autre : le jeton n'est jamais rendu à la page.

   Les agapes ne se posent qu'à qui vient. Dire « excusé » efface donc
   le couvert : compter un couvert pour un absent, c'est le payer. */
async function enregistrer(context, jeton, corps){
  let reponse;
  if (corps.reponse === undefined || corps.reponse === null) reponse = undefined;
  else if (REPONSES.includes(corps.reponse)) reponse = corps.reponse;
  else return { erreur: 'reponse_inconnue' };

  let agapes;
  if (corps.agapes === undefined || corps.agapes === null) agapes = undefined;
  else if (typeof corps.agapes === 'boolean') agapes = corps.agapes ? 1 : 0;
  else return { erreur: 'agapes_inconnues' };

  if (reponse === 'excuse') agapes = null;        // un absent n'a pas de couvert

  const sets = [], liens = [];
  if (reponse !== undefined){ sets.push('reponse = ?'); liens.push(reponse); }
  if (agapes !== undefined){ sets.push('agapes = ?'); liens.push(agapes); }
  if (!sets.length) return null;
  sets.push("repondu_le = datetime('now')");
  /* La réponse change : elle n'est plus versée au registre tant que la
     Secrétaire ne l'a pas reprise. Sans cela, un avis changé après
     coup resterait invisible pour elle. */
  sets.push('versee = 0');

  await context.env.DB.prepare(
    'UPDATE reponses SET ' + sets.join(', ') + ' WHERE jeton = ?')
    .bind(...liens, jeton).run();
  return { ok: true };
}
