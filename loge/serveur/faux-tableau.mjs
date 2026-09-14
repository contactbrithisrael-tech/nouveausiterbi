/* ═══════════════════════════════════════════════════════════════════
   UN TABLEAU D'ATELIER INVENTÉ, POUR LES ÉPREUVES

   L'épreuve du partage se faisait jusqu'ici avec le vrai tableau de
   Bereshit — un fichier qui ne peut pas être versé au dépôt : il porte
   des dates de naissance, des adresses et des convictions
   philosophiques. Résultat, l'épreuve ne se rejouait que sur la
   machine où ce fichier se trouvait, et nulle part ailleurs.

   Douze fiches inventées suffisent : ce qu'on éprouve est la mécanique
   du partage, pas l'identité des Sœurs et Frères. Les noms sont ceux
   des mois du calendrier hébraïque — personne ne s'appelle ainsi, et
   l'on voit du premier coup d'œil qu'ils sont faux.

   Usage :  node loge/serveur/faux-tableau.mjs > /tmp/tableau.json
═══════════════════════════════════════════════════════════════════ */

const NOMS = ['TICHRI','HECHVAN','KISLEV','TEVET','CHEVAT','ADAR',
              'NISSAN','IYAR','SIVAN','TAMOUZ','AV','ELOUL'];
const PRENOMS = ['Alef','Bet','Guimel','Dalet','Hé','Vav',
                 'Zayin','Het','Tet','Yod','Kaf','Lamed'];

const membres = NOMS.map((nom, i) => {
  const n = i + 1;
  const m = {
    id: n, nom, prenoms: PRENOMS[i],
    statut: 'actif',
    degre: n <= 2 ? 1 : (n <= 4 ? 2 : 3),
    du: 480, regle: 0
  };
  /* De quoi éprouver l'affichage : un prénom usuel, un exonéré, des
     fiches incomplètes — le cas ordinaire d'un Atelier réel. */
  if (n === 2) m.dit = 'Beth';
  if (n === 1){ m.qualite = 'Membre honoraire'; m.du = 0;
                m.excusePermanent = true; m.motifExcuse = 'Éloigné de l’Orient'; }
  if (n <= 6){ m.email = `${PRENOMS[i].toLowerCase()}@exemple.test`;
               m.tel = '06 00 00 00 ' + String(n).padStart(2, '0');
               m.adresse = `${n} rue de l’Épreuve`; m.ville = 'VENTABREN';
               m.naissance = `19${60 + n}-0${(n % 9) + 1}-1${n % 9}`; }
  if (n === 3) m.office = 'venerable';
  if (n === 4) m.office = 'premier_surveillant';
  if (n === 5) m.office = 'second_surveillant';
  if (n === 6) m.office = 'maitre_ceremonies';
  return m;
});

process.stdout.write(JSON.stringify({
  _format: 'gestion-loge-rbi',
  _version: 1,
  _le: '2026-09-01T10:00:00.000Z',
  donnees: { membres, presences: {}, agapes: {}, envoyes: {},
             convoquee: false, journal: [], visiteurs: [], amies: [],
             invitationsRecues: [] },
  pieces: {}
}, null, 1));
