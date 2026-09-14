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
  /* Un Souverain Grand Commandeur au Tableau : c'est de là que les
     documents tirent sa qualité et son contreseing. */
  if (n === 12){ m.grade = '33°'; m.qualite = 'Souverain Grand Commandeur'; }
  if (n === 3) m.office = 'venerable';
  if (n === 4) m.office = 'premier_surveillant';
  if (n === 5) m.office = 'second_surveillant';
  if (n === 6) m.office = 'maitre_ceremonies';
  return m;
});

/* Trois Visiteurs annoncés : de quoi éprouver la feuille d'émargement
   qui leur est réservée, et le carnet. Inventés eux aussi. */
const visiteurs = [
  { id: 1, prenom: 'Reouven', nom: 'MISHPAT', grade: 'Maître', rite: 'RBI',
    loge: 'L∴ EXEMPLE n°01', orient: 'Nulle Part', obedience: 'Obédience d’épreuve',
    email: 'reouven@exemple.test', tel: '', invitePar: 'Guimel TICHRI',
    tuilePar: 'Guimel KISLEV', presentTenue: true, visites: [] },
  { id: 2, prenom: 'Chimon', nom: 'EDOUT', grade: 'Compagnon', rite: 'RBI',
    loge: 'L∴ SECONDE n°02', orient: 'Ailleurs', obedience: 'Obédience d’épreuve',
    email: 'chimon@exemple.test', tel: '', invitePar: '',
    tuilePar: 'Dalet TEVET', presentTenue: true, visites: [] },
  { id: 3, prenom: 'Lévi', nom: 'HOQIM', grade: 'Apprenti', rite: 'RBI',
    loge: 'L∴ TROISIÈME n°03', orient: 'Loin', obedience: '',
    email: '', tel: '', invitePar: '', tuilePar: '',
    presentTenue: false, visites: [] }
];

process.stdout.write(JSON.stringify({
  _format: 'gestion-loge-rbi',
  _version: 1,
  _le: '2026-09-01T10:00:00.000Z',
  donnees: { membres, presences: {}, agapes: {}, envoyes: {},
             convoquee: false, journal: [], visiteurs, amies: [],
             invitationsRecues: [] },
  pieces: {}
}, null, 1));
