/* L'EPREUVE DU MIROIR — node loge/serveur/essai-miroir.mjs
 *
 * « loge/beta.html » est la copie hors ligne du programme : un seul
 * fichier, enregistre sur un ordinateur et ouvert d'un double-clic. Il
 * doit etre le MEME que « secretariat.html », octet pour octet.
 *
 * CE QUI EST ARRIVE, ET QUI JUSTIFIE CETTE EPREUVE. Les deux fichiers
 * sont tenus a la main. Une fusion git a resolu deux hunks differemment
 * dans l'un et dans l'autre : secretariat.html portait les deux
 * changements, beta.html n'en portait qu'un. Rien ne l'a signale.
 *
 * Personne ne l'aurait vu avant qu'une Soeur, travaillant hors ligne le
 * soir d'une tenue, ne cherche un bouton qui n'existe pas chez elle —
 * ou pire, ne croie enregistrer ce qui n'est pas enregistre.
 *
 * Deux copies tenues a la main finissent TOUJOURS par diverger. Faute
 * d'une etape de fabrication dans ce depot, c'est cette epreuve qui
 * tient le role : elle ne repare rien, elle refuse de se taire. */
import fs from 'node:fs';

const RACINE = new URL('../../', import.meta.url).pathname;
const A = RACINE + 'secretariat.html';
const B = RACINE + 'loge/beta.html';

const a = fs.readFileSync(A, 'utf8');
const b = fs.readFileSync(B, 'utf8');

if (a === b){
  console.log('  OK   loge/beta.html est le miroir exact de secretariat.html');
  console.log('\n  tout passe');
  process.exit(0);
}

/* On ne dit pas « ils different » : on dit OU, et de combien. Un refus
   qui n'indique rien se contourne en recopiant au hasard. */
const la = a.split('\n'), lb = b.split('\n');
let i = 0;
while (i < la.length && i < lb.length && la[i] === lb[i]) i++;

console.log('  NON  loge/beta.html N’EST PLUS LE MIROIR de secretariat.html');
console.log(`       premiere difference a la ligne ${i + 1} :`);
console.log(`         secretariat.html : ${(la[i] ?? '(fin du fichier)').trim().slice(0, 90)}`);
console.log(`         loge/beta.html   : ${(lb[i] ?? '(fin du fichier)').trim().slice(0, 90)}`);
console.log(`       ${la.length} lignes contre ${lb.length}.`);
console.log('\n  Pour reparer :  cp secretariat.html loge/beta.html');
console.log('\n  1 echec(s)');
process.exit(1);
