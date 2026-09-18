/* ═══════════════════════════════════════════════════════════════════
   RÉPONDRE À LA CONVOCATION

   Cette route est la SEULE du programme qui s'ouvre sans session : une
   Sœur qui reçoit sa convocation n'a pas de compte, et n'a pas à en
   avoir un pour dire qu'elle vient.

   ► C'EST LE JETON QUI AUTORISE, et lui seul. Trente-deux octets tirés
     au hasard, remis dans le courriel de cette personne-là. Il ne dit
     rien de plus que : « celui qui tient ce lien répond pour cette
     ligne-ci ». Il ne permet pas de lire le registre, ni de voir qui
     d'autre a répondu, ni de répondre pour un autre.

   ► ON NE REND QUE CE QU'IL FAUT POUR AFFICHER LA PAGE : le prénom, la
     date de la tenue, et ce qui a déjà été répondu. Pas la liste des
     présents, pas les adresses des autres. Un lien retrouvé dans une
     boîte aux lettres ne doit pas ouvrir le Tableau de l'Atelier.

   ► RÉPONDRE DEUX FOIS CHANGE LA RÉPONSE. On change d'avis ; c'est le
     propre d'une réponse, et ce n'est pas une erreur à refuser.
═══════════════════════════════════════════════════════════════════ */

import { json } from './_commun.js';

const REPONSES = ['present', 'excuse'];

/* ── LE LIEN OÙ L'ON RÈGLE SA PART ─────────────────────────────────
   Il est utile à l'instant précis où quelqu'un vient de dire qu'il
   reste à table — pas trois écrans plus loin, pas dans un courriel
   qu'il faudra retrouver.

   On le tire du registre de l'Atelier, et on ne rend QUE lui. Le
   registre porte le Tableau, les adresses, les présences : rien de
   cela ne doit sortir par cette route, qui s'ouvre sans compte. Une
   adresse web publique, et rien d'autre. */
async function lienDePaiement(context, jeton){
  try {
    const r = await context.env.DB.prepare(
      'SELECT donnees FROM etat WHERE loge_id = ' +
      '(SELECT loge_id FROM reponses WHERE jeton = ?)').bind(jeton).first();
    if (!r) return null;
    const lien = JSON.parse(r.donnees)?.tenue?.agapesPaiement;
    if (typeof lien !== 'string') return null;
    /* Seulement une adresse web en clair : ni « javascript: », ni
       « data: », qui feraient de ce bouton autre chose qu'un lien. */
    return /^https:\/\/[^\s"'<>]+$/.test(lien.trim()) ? lien.trim() : null;
  } catch (e) { return null; }
}

/* On répond peu, et lentement : ce qui sort d'ici ne doit pas servir à
   deviner un jeton. Une réponse identique pour un jeton faux et pour un
   jeton périmé n'apprend rien à qui essaie au hasard. */
const INCONNU = { erreur: 'lien_inconnu' };

function jetonDe(requete){
  const u = new URL(requete.url);
  const j = (u.searchParams.get('j') || '').trim();
  return /^[a-f0-9]{64}$/.test(j) ? j : null;
}

async function ligne(context, jeton){
  return await context.env.DB.prepare(
    'SELECT jeton, tenue, qui_type, nom, reponse, agapes FROM reponses WHERE jeton = ?')
    .bind(jeton).first();
}

export async function onRequestGet(context){
  const j = jetonDe(context.request);
  if (!j) return json(INCONNU, 404);
  const r = await ligne(context, j);
  if (!r) return json(INCONNU, 404);

  /* Le nom de l'Atelier et la date viennent d'ici : la page qui
     s'affiche n'a rien à deviner, et rien d'autre à demander. */
  const loge = await context.env.DB.prepare(
    'SELECT nom, numero, orient FROM loges WHERE id = ' +
    '(SELECT loge_id FROM reponses WHERE jeton = ?)').bind(j).first();

  return json({
    nom: r.nom || '', tenue: r.tenue, qualite: r.qui_type,
    reponse: r.reponse || null,
    agapes: r.agapes === null || r.agapes === undefined ? null : !!r.agapes,
    paiement: await lienDePaiement(context, j),
    loge: loge ? { nom: loge.nom, numero: loge.numero, orient: loge.orient } : null
  });
}

export async function onRequestPost(context){
  const j = jetonDe(context.request);
  if (!j) return json(INCONNU, 404);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  const reponse = REPONSES.includes(corps?.reponse) ? corps.reponse : null;
  if (!reponse) return json({ erreur: 'reponse_inconnue', attendu: REPONSES }, 400);

  /* Aux agapes seulement si l'on vient : répondre « excusé, et je reste
     à table » ferait compter un couvert pour quelqu'un d'absent. */
  const agapes = reponse === 'present' ? (corps?.agapes ? 1 : 0) : 0;

  const res = await context.env.DB.prepare(
    `UPDATE reponses SET reponse = ?, agapes = ?, repondu_le = datetime('now'),
            versee = 0
      WHERE jeton = ?`).bind(reponse, agapes, j).run();

  const ecrite = res?.meta?.changes ?? 0;
  if (!ecrite) return json(INCONNU, 404);

  const r = await ligne(context, j);
  return json({ enregistre: true, nom: r.nom || '', tenue: r.tenue,
                reponse: r.reponse, agapes: !!r.agapes,
                paiement: await lienDePaiement(context, j) });
}
