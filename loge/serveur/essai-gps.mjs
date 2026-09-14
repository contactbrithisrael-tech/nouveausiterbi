/* ═══════════════════════════════════════════════════════════════════
   L'ÉPREUVE DU POINT DU TEMPLE

   Sur un téléphone, on ne relève pas deux nombres : on appuie sur
   « Partager », et l'on obtient un lien. Le champ doit donc accepter
   le point sous la forme où il arrive vraiment — et REFUSER ce qu'il
   ne comprend pas, plutôt que d'imprimer sur une convocation un point
   mal lu. Un Frère envoyé dans un chemin de vigne à 19 h 30 ne revient
   pas.

   On extrait la fonction de la page et on l'éprouve seule : le
   navigateur n'apprendrait rien de plus, et l'épreuve tient en une
   seconde.

       node loge/serveur/essai-gps.mjs
═══════════════════════════════════════════════════════════════════ */
import fs from 'node:fs';

const RACINE = new URL('../../', import.meta.url).pathname;
const page = fs.readFileSync(RACINE + 'secretariat.html', 'utf8');
const debut = page.indexOf('const FRANCE = {');
const fin   = page.indexOf('/* ── OÙ SE TROUVE LE TEMPLE');
if (debut < 0 || fin < 0 || fin < debut){
  console.error('La lecture du point a changé de place dans la page.');
  process.exit(1);
}
const { lirePointGps } = await import(
  'data:text/javascript,' + encodeURIComponent(
    page.slice(debut, fin) + '\nexport { lirePointGps };'));

const CAS = [
  // les deux nombres, sous leurs formes courantes
  ['43.512340, 5.398760',                              '43.512340, 5.398760'],
  ['43.51234,5.39876',                                 '43.512340, 5.398760'],
  ['43.51234 5.39876',                                 '43.512340, 5.398760'],
  ['43,51234 5,39876',                                 '43.512340, 5.398760'],
  ['  43.51234 ; 5.39876  ',                           '43.512340, 5.398760'],

  // les degrés, minutes, secondes — ici le clocher de Ventabren
  ['43°32\'17"N 5°17\'35"E',                           '43.538056, 5.293056'],
  ['43° 32\' 17.5" N, 5° 17\' 35.2" E',                '43.538194, 5.293111'],
  ['43°32’17”N 5°17’35”E',                             '43.538056, 5.293056'],

  // un lien collé, de quelque plan que ce soit
  ['https://www.google.com/maps/@43.51234,5.39876,17z',       '43.512340, 5.398760'],
  ['https://maps.google.com/?q=43.51234,5.39876',             '43.512340, 5.398760'],
  ['https://maps.apple.com/?ll=43.51234,5.39876&q=Venaqui',   '43.512340, 5.398760'],
  ['geo:43.51234,5.39876',                                    '43.512340, 5.398760'],
  ['https://www.google.com/maps/place/X/@43.51234,5.39876,17z/data=!3m1!4b1',
                                                              '43.512340, 5.398760'],

  // ce qui n'est pas un point ne doit JAMAIS en devenir un
  ['route d\'Eguilles',        null],
  ['1229',                     null],
  ['1229 route d\'Eguilles',   null],
  ['13122 VENTABREN',          null],
  ['',                         null],
  ['   ',                      null],
  ['200.0, 5.0',               null],   // latitude impossible
  ['43.5, 400.0',              null],   // longitude impossible
  ['https://www.ventabren.fr/', null],  // un lien sans point
];

let ko = 0;
const v = (c, n, d = '') => {
  console.log(`  ${c ? '✓' : '✗'} ${n}${c ? '' : '  <- ' + d}`);
  if (!c) ko++;
};

for (const [entree, attendu] of CAS){
  const o = lirePointGps(entree);
  const eu = o ? o.texte : null;
  v(eu === attendu,
    (attendu === null ? 'refusé : ' : 'lu : ') +
      JSON.stringify(entree).slice(0, 56),
    `${eu} au lieu de ${attendu}`);
}

/* Le sens des nombres n'est pas deviné. Deux nombres échangés se
   corrigent en une seconde ; un point « corrigé » à tort envoie
   l'Atelier ailleurs sans que personne ne s'en doute. */
const inverse = lirePointGps('5.39876, 43.51234');
v(inverse !== null && inverse.chezNous === false,
  'DEUX NOMBRES INVERSÉS : signalés, jamais corrigés d’office', JSON.stringify(inverse));
const bon = lirePointGps('43.51234, 5.39876');
v(bon !== null && bon.chezNous === true,
  'un point qui tombe en France est reconnu comme tel');

/* Six décimales : dix centimètres. Au-delà on écrirait du bruit. */
v(lirePointGps('43.5123456789, 5.3987654321').texte === '43.512346, 5.398765',
  'le point est arrondi à six décimales — dix centimètres suffisent',
  lirePointGps('43.5123456789, 5.3987654321').texte);

console.log(ko ? `\n  ${ko} échec(s)` : '\n  tout passe');
process.exit(ko ? 1 : 0);
