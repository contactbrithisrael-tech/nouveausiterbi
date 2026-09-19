/* ═══════════════════════════════════════════════════════════════════
   LIRE UNE CONVOCATION REÇUE

   Une convocation d'Atelier ami arrive en photo ou en PDF scanné. La
   saisir à la main, c'est recopier ce qu'une machine sait lire — et
   personne ne le fait le soir où il faudrait.

   ► LA CLÉ NE QUITTE JAMAIS LE SERVEUR. Elle est un Secret Cloudflare,
     comme celle du service d'envoi. Le navigateur envoie l'image, le
     serveur appelle Claude, et rend les renseignements. Une clé posée
     dans la page serait lisible par quiconque ouvre le programme.

   ► LA ROUTE EXIGE UNE SESSION. Lire une convocation, c'est dépenser
     de l'argent ; ce n'est pas un service public. Sans session, rien.

   ► ON NE REND QUE DES RENSEIGNEMENTS, jamais le texte brut ni la
     réponse du modèle telle quelle : un schéma fixe, des clés connues,
     et ce qui n'y entre pas est jeté.

   ► LE MODÈLE NE DOIT RIEN INVENTER. La consigne le dit, et le schéma
     autorise null partout : un blanc se corrige à la main, une
     invention vraisemblable passe inaperçue et entre au registre.
═══════════════════════════════════════════════════════════════════ */

import { sessionCourante, json } from './_commun.js';

const MODELE = 'claude-opus-5';
const POIDS_MAX = 5 * 1024 * 1024;        // 5 Mo d'image, largement assez
const TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

/* Les clés rendues, et elles seules. Le programme les range ensuite
   dans la fiche de l'Atelier et dans sa convocation. */
const SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    nom:        { type: ['string', 'null'] },
    orient:     { type: ['string', 'null'] },
    obedience:  { type: ['string', 'null'] },
    rite:       { type: ['string', 'null'] },
    temple:     { type: ['string', 'null'] },
    adresse:    { type: ['string', 'null'] },
    codePostal: { type: ['string', 'null'] },
    ville:      { type: ['string', 'null'] },
    contactNom:   { type: ['string', 'null'] },
    contactEmail: { type: ['string', 'null'] },
    contactTel:   { type: ['string', 'null'] },
    date:  { type: ['string', 'null'] },
    heure: { type: ['string', 'null'] },
    degre: { type: ['integer', 'null'] },
    objet: { type: ['string', 'null'] },
    odj:   { type: ['string', 'null'] }
  },
  required: ['nom','orient','obedience','rite','temple','adresse','codePostal',
             'ville','contactNom','contactEmail','contactTel','date','heure',
             'degre','objet','odj']
};

const CONSIGNE = `Tu lis la photo d'une convocation maçonnique française.

QUATRE CLÉS AVANT TOUTES LES AUTRES : "nom" (la Loge), "date", le lieu
("temple", "adresse", "codePostal", "ville") et "contactEmail". Ce sont
elles qui permettent d'écrire à cet Atelier et de porter sa tenue à un
agenda. Le reste est du confort. Si la photo est mauvaise, mets ton
attention là.

N'INVENTE RIEN. Toute clé dont la réponse n'est pas écrite sur l'image
reste null — y compris les quatre ci-dessus : importantes ne veut pas
dire à deviner. Un blanc se corrige à la main ; une invention
vraisemblable passe inaperçue et entre au registre.

- "nom" : le nom de la Loge tel qu'écrit, titre compris, mais SANS son
  Orient. « Les Écossais de la Sainte Baume à l'Orient de Saint Maximin »
  donne nom = « Les Écossais de la Sainte Baume », orient = « Saint Maximin ».
- "orient" : ce qui suit « à l'Orient de ». Il s'écrit souvent autrement
  que la ville postale : garde chacun sous sa clé, tel qu'écrit.
- L'adresse postale tient d'ordinaire sur UNE SEULE ligne, en bas de
  page. Sépare-la : "adresse" = rue et quartier, "codePostal" = les cinq
  chiffres, "ville" = ce qui suit.
- "temple" : le nom du local, et lui seul. « en un lieu très pur, très
  saint et très éclairé » est une formule rituelle, non un nom de
  temple : dans ce cas "temple" reste null. C'est l'invention la plus
  tentante de toutes.
- "contactNom", "contactEmail", "contactTel" : LA MÊME PERSONNE, celle
  à qui l'on écrit pour cet Atelier — son Secrétaire d'ordinaire. Ne
  marie pas un nom trouvé ici avec un numéro trouvé là.

  CAS RÉEL : une convocation nomme son Secrétaire et son courriel en
  bas de page, et porte ailleurs « réserver votre repas par SMS auprès
  de notre Sœur Marie au 06 76 00 61 66 ». Ce numéro est celui de Sœur
  Marie ; il n'a rien à faire dans "contactTel". Un numéro donné pour
  les agapes, les transports ou l'hébergement appartient à qui le
  donne, non au secrétariat.

  Si le seul numéro de la page est rattaché à quelqu'un d'autre que le
  contact, "contactTel" reste null. Un champ vide se remplit d'un coup
  de téléphone ; un mauvais numéro se découvre le soir de la tenue.
- "date" : la tenue, au format AAAA-MM-JJ. Une date maçonnique porte
  souvent l'an de la Vraie Lumière (année civile + 4000) : ne la rends
  pas telle quelle. Si l'année civile n'est pas déductible, laisse null.
- "heure" : format HH:MM, sur vingt-quatre heures.
- "degre" : 1, 2 ou 3 selon le degré des travaux. Sinon null.
- "objet" : ce qui se tient ce soir-là, en quelques mots.
- "odj" : l'ordre du jour, si la convocation en porte un.`;

/* La route dit si elle est servie, avant qu'on propose un bouton qui
   n'aboutirait pas. */
export async function onRequestGet(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);
  return json({ configure: !!context.env.CLE_ANTHROPIC, service: 'claude' });
}

export async function onRequestPost(context){
  const moi = await sessionCourante(context);
  if (!moi) return json({ erreur: 'non_connecte' }, 401);

  const cle = context.env.CLE_ANTHROPIC;
  if (!cle) return json({ configure: false, erreur: 'lecture_non_configuree' }, 501);

  let corps;
  try { corps = await context.request.json(); }
  catch (e) { return json({ erreur: 'requete_illisible' }, 400); }

  /* L'image arrive en base64, avec son type. On borne les deux : une
     route qui accepte n'importe quel poids est une facture ouverte. */
  const type = String(corps?.media_type || '').trim();
  const donnee = String(corps?.image || '').replace(/^data:[^,]+,/, '');
  if (!TYPES.includes(type))
    return json({ erreur: 'type_refuse', acceptes: TYPES }, 415);
  if (!donnee) return json({ erreur: 'image_manquante' }, 400);
  if (donnee.length * 0.75 > POIDS_MAX)
    return json({ erreur: 'image_trop_lourde', maximum: POIDS_MAX }, 413);

  let r;
  try {
    r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': cle,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: MODELE,
        max_tokens: 4096,
        output_config: { format: { type: 'json_schema', schema: SCHEMA } },
        messages: [{ role: 'user', content: [
          { type: 'image', source: { type: 'base64', media_type: type, data: donnee } },
          { type: 'text', text: CONSIGNE }
        ] }]
      })
    });
  } catch (e) {
    return json({ erreur: 'service_injoignable' }, 502);
  }

  if (!r.ok){
    /* On rend la raison telle que le service la donne, non une
       invention : « la clé est refusée » et « trop de lectures » ne se
       réparent pas de la même façon. */
    let detail = '';
    try { const d = await r.json(); detail = d?.error?.message || ''; }
    catch (e) { /* le service n'a pas répondu en JSON */ }
    return json({ erreur: 'service_refuse', statut: r.status, detail }, 502);
  }

  let rep;
  try { rep = await r.json(); }
  catch (e) { return json({ erreur: 'reponse_illisible' }, 502); }

  /* Une déclinaison de politique n'est pas une panne : on le dit. */
  if (rep?.stop_reason === 'refusal')
    return json({ erreur: 'lecture_declinee' }, 422);

  const texte = (rep?.content || [])
    .filter(b => b && b.type === 'text').map(b => b.text).join('');
  let lu;
  try { lu = JSON.parse(texte); }
  catch (e) { return json({ erreur: 'lecture_incomprise' }, 502); }

  /* Le schéma est tenu par le service, mais on ne s'en remet pas à
     lui : ce qui n'est pas une clé attendue n'entre pas. */
  const propre = {};
  for (const k of Object.keys(SCHEMA.properties)){
    const v = lu[k];
    if (v === null || v === undefined || v === '') continue;
    propre[k] = k === 'degre' ? Number(v) : String(v).slice(0, 400);
  }
  return json({ lu: propre, usage: {
    entree: rep?.usage?.input_tokens ?? null,
    sortie: rep?.usage?.output_tokens ?? null } });
}
