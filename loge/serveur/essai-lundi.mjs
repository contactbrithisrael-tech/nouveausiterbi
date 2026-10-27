/* L'EPREUVE DU PREMIER LUNDI — node loge/serveur/essai-lundi.mjs
 *
 * « Les tenues et les agapes sont toujours le 1er lundi du mois. »
 * C'est la regle de l'Atelier, et elle etait dans une tete, nulle part
 * ailleurs : la date se tapait a la main chaque mois.
 *
 * On eprouve le calcul seul, hors navigateur : une date fausse ne se
 * voit pas a l'ecran, elle se voit six mois plus tard quand personne ne
 * vient. Les cas pieges sont ici — le mois qui COMMENCE un lundi, et
 * decembre, qui est suivi de janvier d'une autre annee. */
import fs from 'node:fs';

const RACINE = new URL('../../', import.meta.url).pathname;
const page = fs.readFileSync(RACINE + 'secretariat.html', 'utf8');

/* On prend les fonctions dans le programme lui-meme, pas une copie :
   une copie finirait par diverger de ce qui tourne vraiment. */
const bloc = page.slice(page.indexOf('function premierLundi('),
                        page.indexOf('function passerALaTenueSuivante('));
const { premierLundi, premierLundiSuivant, estPremierLundi, ecartJours } =
  new Function(bloc + '; return { premierLundi, premierLundiSuivant, ' +
               'estPremierLundi, ecartJours };')();

let ko = 0;
const v = (c, n, d) => {
  console.log(`  ${c ? 'OK ' : 'NON'}  ${n}` + (c ? '' : '  <- ' + JSON.stringify(d)));
  if (!c) ko++;
};

/* Les douze prochains, calcules a la main sur un calendrier. */
const ATTENDUS = {
  '2026-11': '2026-11-02', '2026-12': '2026-12-07', '2027-01': '2027-01-04',
  '2027-02': '2027-02-01', '2027-03': '2027-03-01', '2027-04': '2027-04-05',
  '2027-05': '2027-05-03', '2027-06': '2027-06-07', '2027-07': '2027-07-05',
  '2027-08': '2027-08-02', '2027-09': '2027-09-06', '2027-10': '2027-10-04'
};
let tous = true;
for (const [mois, attendu] of Object.entries(ATTENDUS)){
  const [a, m] = mois.split('-').map(Number);
  if (premierLundi(a, m) !== attendu){ tous = false; v(false, 'premier lundi de ' + mois, premierLundi(a, m)); }
}
v(tous, 'LES DOUZE PROCHAINS PREMIERS LUNDIS SONT JUSTES');

/* LE MOIS QUI COMMENCE UN LUNDI. Le piege : avancer « jusqu'au
   prochain lundi » donnerait le 8, et la tenue partirait d'une
   semaine. Fevrier 2027 et mars 2027 commencent un lundi. */
v(premierLundi(2027, 2) === '2027-02-01',
  "UN MOIS QUI COMMENCE UN LUNDI : c'est le 1er, non le 8",
  premierLundi(2027, 2));
v(premierLundi(2027, 3) === '2027-03-01',
  'et le mois suivant aussi', premierLundi(2027, 3));

/* DECEMBRE EST SUIVI DE JANVIER, D'UNE AUTRE ANNEE. Le piege :
   ajouter un au mois donnerait un treizieme mois. */
v(premierLundiSuivant('2026-12-07') === '2027-01-04',
  "DECEMBRE EST SUIVI DE JANVIER, ET L'ANNEE CHANGE",
  premierLundiSuivant('2026-12-07'));

/* ON PART DU MOIS DE LA DATE, NON DE TRENTE JOURS APRES. Un mois ne
   fait pas trente jours : trente jours apres le 2 fevrier, on est en
   mars, et l'on sauterait une tenue. */
v(premierLundiSuivant('2027-02-01') === '2027-03-01',
  "FEVRIER EST SUIVI DE MARS : on ne compte pas trente jours",
  premierLundiSuivant('2027-02-01'));

/* La tenue en cours de l'Atelier. */
v(estPremierLundi('2026-11-02'), 'le 2 novembre 2026 est bien un premier lundi');
v(!estPremierLundi('2026-11-09'), 'le 9 novembre ne l’est pas');
v(!estPremierLundi(''), 'une date absente ne passe pas pour un premier lundi');
v(!estPremierLundi('pas une date'), 'un texte non plus');

/* L'ECART DE LA LIMITE D'INSCRIPTION. Il n'est pas une regle qu'on
   invente : c'est celui que la Secretaire a choisi, et qu'on reconduit. */
v(ecartJours('2026-11-02', '2026-10-30') === -3,
  "l'ecart de la limite d'inscription se compte en jours, meme a cheval "
  + 'sur deux mois', ecartJours('2026-11-02', '2026-10-30'));
v(ecartJours('2026-11-02', '') === null,
  'et une limite absente ne vaut pas zero', ecartJours('2026-11-02', ''));

console.log(ko ? `\n  ${ko} echec(s)` : '\n  tout passe');
process.exit(ko ? 1 : 0);
