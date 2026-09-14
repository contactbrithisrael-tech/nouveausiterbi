/* ═══════════════════════════════════════════════════════════════════
   REDONNER UN MOT DE PASSE À QUELQU'UN QUI L'A PERDU

   Il n'y a PAS de « mot de passe oublié » dans ce programme, et ce
   n'est pas un oubli. Le renvoyer supposerait de pouvoir le relire ;
   or la base n'en garde qu'une empreinte salée, que personne — pas
   même qui tient le site — ne sait renverser. C'est le prix de la
   sûreté, et il se paie une fois, à la main.

   Ce petit outil calcule l'empreinte d'un mot de passe neuf et écrit
   la ligne SQL à coller dans la console D1. Rien n'est envoyé nulle
   part : il ne fait que du calcul.

       node loge/serveur/nouveau-mdp.mjs secretariat@exemple.test "le mot neuf"

   Ensuite, dites-le de vive voix à l'intéressé — jamais par courriel,
   puisqu'un courriel ne s'efface pas — et demandez-lui de le changer
   lui-même par « Mon mot de passe » dès sa première entrée.

   Le même outil sert à créer un compte : la seconde ligne imprimée
   est l'INSERT, avec la charge à corriger si besoin.
═══════════════════════════════════════════════════════════════════ */
import { empreinteMdp } from '../../functions/api/_commun.js';

const [, , courriel, mdp, charge = 'secretariat', nom = ''] = process.argv;

if (!courriel || !mdp){
  console.error('usage : node loge/serveur/nouveau-mdp.mjs <courriel> "<mot de passe>"' +
                ' [charge] ["Nom affiché"]');
  console.error('        charge : secretariat | tresorerie | venerable');
  process.exit(1);
}
if ([...mdp].length < 10){
  console.error('Dix caractères au moins — c\'est ce que le programme exigera d\'eux.');
  process.exit(1);
}

const hex = t => [...new Uint8Array(t)].map(o => o.toString(16).padStart(2, '0')).join('');
const sel = hex(crypto.getRandomValues(new Uint8Array(16)));
const h   = await empreinteMdp(mdp, sel);

const q = s => "'" + String(s).replace(/'/g, "''") + "'";

console.log('\n── Pour REMPLACER le mot de passe d\'un compte existant ──\n');
console.log(`UPDATE utilisateurs SET mdp_hash = ${q(h)}, mdp_sel = ${q(sel)}`);
console.log(`    WHERE courriel = ${q(courriel)};`);
console.log('\n── Pour CRÉER un compte ──\n');
console.log('INSERT INTO utilisateurs (loge_id, courriel, nom, charge, mdp_hash, mdp_sel)');
console.log(`VALUES (1, ${q(courriel)}, ${q(nom || courriel)}, ${q(charge)}, ${q(h)}, ${q(sel)});`);
console.log('\nLe mot de passe lui-même n\'est écrit nulle part ci-dessus.\n');
