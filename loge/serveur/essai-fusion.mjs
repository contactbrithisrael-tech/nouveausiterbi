/* L'EPREUVE DE LA FUSION — node loge/serveur/essai-fusion.mjs
 *
 * CE QU'ON EPROUVE. Le registre s'ecrivait en bloc : a deux, l'un des
 * deux perdait son travail. On fusionne desormais trois documents — le
 * socle, le leur, le mien — pour savoir QUI A CHANGE QUOI.
 *
 * Chaque cas ci-dessous est une situation reelle de secretariat, non un
 * exercice : la Soeur Secretaire note un telephone pendant que le
 * Tresorier saisit un reglement, quelqu'un retire une fiche pendant
 * qu'un autre la complete, deux Officiers ajoutent le meme visiteur. */
import { fusionner } from '../../functions/api/_fusion.js';

let ko = 0;
const v = (c, n, d) => {
  console.log(`  ${c ? 'OK ' : 'NON'}  ${n}` +
              (c ? '' : '  <- ' + JSON.stringify(d)));
  if (!c) ko++;
};
const cp = o => JSON.parse(JSON.stringify(o));

/* == 1. DEUX CHAMPS DIFFERENTS : LES DEUX TIENNENT ================== */
{
  const socle = { membres: [{ id: 1, nom: 'TICHRI', tel: '', regle: 0 }] };
  const leur = cp(socle); leur.membres[0].regle = 480;      // le Tresorier
  const mien = cp(socle); mien.membres[0].tel = '06 11 22'; // la Secretaire
  const e = [];
  const f = fusionner(socle, leur, mien, e);
  v(f.membres[0].regle === 480 && f.membres[0].tel === '06 11 22',
    "LE REGLEMENT DU TRESORIER ET LE TELEPHONE DE LA SECRETAIRE TIENNENT ENSEMBLE",
    f.membres[0]);
  v(e.length === 0, "et rien n'a eu besoin d'etre tranche", e);
}

/* == 2. LE MEME CHAMP, DES DEUX COTES : LE DERNIER L'EMPORTE, ET ON LE DIT */
{
  const socle = { tenue: { heureOuv: '19:30' } };
  const leur = { tenue: { heureOuv: '20:00' } };
  const mien = { tenue: { heureOuv: '19:00' } };
  const e = [];
  const f = fusionner(socle, leur, mien, e);
  v(f.tenue.heureOuv === '19:00', "le dernier qui ecrit l'emporte", f.tenue);
  v(e.includes('tenue.heureOuv'),
    "ET L'ARBITRAGE EST CONSIGNE AVEC SON CHEMIN : ce qui se perd ne se " +
    "perd pas en silence", e);
}

/* == 3. CHACUN AJOUTE UNE FICHE : AUCUNE NE DISPARAIT =============== */
{
  const socle = { visiteurs: [{ id: 1, nom: 'A' }] };
  const leur = { visiteurs: [{ id: 1, nom: 'A' }, { id: 2, nom: 'B' }] };
  const mien = { visiteurs: [{ id: 1, nom: 'A' }, { id: 3, nom: 'C' }] };
  const f = fusionner(socle, leur, mien, []);
  const noms = f.visiteurs.map(x => x.nom).sort().join('');
  v(noms === 'ABC', "LES DEUX AJOUTS TIENNENT", f.visiteurs);
}

/* == 4. LA MEME FICHE AJOUTEE DES DEUX COTES ======================== */
/* Deux Officiers inscrivent le meme Visiteur, chacun de son cote, avec
 * le meme numero et des renseignements differents. Le socle ne la
 * contient pas : sans soin, tout ce que l'un a ecrit disparait. */
{
  const socle = { visiteurs: [] };
  const leur = { visiteurs: [{ id: 1, nom: 'HOQIM', tel: '06 99' }] };
  const mien = { visiteurs: [{ id: 1, nom: 'HOQIM', email: 'h@test' }] };
  const f = fusionner(socle, leur, mien, []);
  v(f.visiteurs.length === 1, "une seule fiche, non deux", f.visiteurs);
  v(f.visiteurs[0].tel === '06 99' && f.visiteurs[0].email === 'h@test',
    "ET LES DEUX RENSEIGNEMENTS Y SONT : un socle absent ne fait pas " +
    "disparaitre la moitie du travail", f.visiteurs[0]);
}

/* == 5. UN RETRAIT EST UN ACTE, ON L'HONORE ========================= */
{
  const socle = { amis: [{ id: 1, nom: 'X' }, { id: 2, nom: 'Y' }] };
  const leur = { amis: [{ id: 1, nom: 'X' }] };                  // l'autre a retire Y
  const mien = { amis: [{ id: 1, nom: 'X2' }, { id: 2, nom: 'Y' }] };
  const f = fusionner(socle, leur, mien, []);
  v(!f.amis.some(x => x.id === 2),
    "LA FICHE RETIREE PAR L'AUTRE NE REVIENT PAS : son retrait est un acte",
    f.amis);
  v(f.amis.find(x => x.id === 1).nom === 'X2',
    "et ma modification sur l'autre fiche tient", f.amis);
}
{
  const socle = { amis: [{ id: 1, nom: 'X' }, { id: 2, nom: 'Y' }] };
  const leur = { amis: [{ id: 1, nom: 'X' }, { id: 2, nom: 'Y2' }] };
  const mien = { amis: [{ id: 1, nom: 'X' }] };                  // c'est moi qui retire
  const f = fusionner(socle, leur, mien, []);
  v(!f.amis.some(x => x.id === 2),
    "et dans l'autre sens aussi : ce que JE retire ne revient pas", f.amis);
}

/* == 6. ON NE RECOLLE PAS UNE FICHE SUR UNE AUTRE =================== */
/* Fusionner deux tableaux case par case est faux des que quelqu'un
 * insere : tout ce qui suit se decale, et l'on recolle le telephone
 * d'un Frere sur la fiche d'un autre. On fusionne par id. */
{
  const socle = { membres: [{ id: 1, nom: 'A', tel: '' }, { id: 2, nom: 'B', tel: '' }] };
  const leur = { membres: [{ id: 9, nom: 'NEUF', tel: '' },
                           { id: 1, nom: 'A', tel: '' },
                           { id: 2, nom: 'B', tel: '' }] };   // insere en tete
  const mien = { membres: [{ id: 1, nom: 'A', tel: '0601' },
                           { id: 2, nom: 'B', tel: '' }] };
  const f = fusionner(socle, leur, mien, []);
  const a = f.membres.find(x => x.id === 1), b = f.membres.find(x => x.id === 2);
  v(a.tel === '0601' && b.tel === '',
    "LE TELEPHONE RESTE SUR LA BONNE FICHE malgre l'insertion de l'autre",
    f.membres);
  v(f.membres.some(x => x.id === 9), "et la fiche inseree est la", f.membres);
}

/* == 7. CE QU'ON N'A PAS TOUCHE NE REPOUSSE RIEN ==================== */
{
  const socle = { tenue: { date: '2026-09-07', titre: 'T' }, membres: [] };
  const leur = { tenue: { date: '2026-11-02', titre: 'T' }, membres: [{ id: 1 }] };
  const mien = cp(socle);                       // on n'a rien change du tout
  const e = [];
  const f = fusionner(socle, leur, mien, e);
  v(f.tenue.date === '2026-11-02' && f.membres.length === 1,
    "UN ENREGISTREMENT QUI NE CHANGE RIEN N'EFFACE RIEN", f);
  v(e.length === 0, "et il n'arbitre rien", e);
}

/* == 8. LES PRESENCES, QUI SONT DES OBJETS A CLES ================== */
/* presences = { "1": "present", "2": "excuse" } : deux Officiers
 * cochent deux personnes differentes au meme moment. */
{
  const socle = { presences: { 1: 'attendu' } };
  const leur = { presences: { 1: 'present' } };
  const mien = { presences: { 1: 'attendu', 2: 'excuse' } };
  const f = fusionner(socle, leur, mien, []);
  v(f.presences[1] === 'present' && f.presences[2] === 'excuse',
    "DEUX OFFICIERS COCHENT DEUX PERSONNES : les deux coches tiennent",
    f.presences);
}

console.log(ko ? `\n  ${ko} echec(s)` : "\n  tout passe");
process.exit(ko ? 1 : 0);
