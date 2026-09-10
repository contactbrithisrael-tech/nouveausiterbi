/* ═══════════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — formules.js

   Les règles d'écriture propres au Rite, réunies ici et nulle part
   ailleurs. Chacune est appliquée à un seul endroit : le jour où l'une
   d'elles change, elle change une fois.

   Aucune de ces règles n'est inventée. Elles viennent des documents de
   la R∴L∴ Bereshit ou du Souverain Grand Commandeur, et la source est
   citée à chaque fois.
════════════════════════════════════════════════════════════════════ */

/* ── L'An de Vraie Lumière ──────────────────────────────────────────
   Source : Constitution V9 et Règlement Général — « L'An de la Vraie
   Lumière 5786 (2026 de l'ère vulgaire) ». C'est l'année HÉBRAÏQUE,
   soit l'année vulgaire plus 3760.

   ► J'avais d'abord écrit +4000, d'après la planche à tracer de
     Bereshit qui porte « AVL 6025 » pour 2025. C'était faux : +4000
     est la convention du Rite Écossais, et ce 6025 est un reste du
     modèle recopié, au même titre que la R∴L∴ Nostradamus qui y
     figurait encore. La Constitution fait foi.

   ► RESTE À TRANCHER : l'année hébraïque ne change pas au 1er janvier
     mais à Roch Hachana, en septembre ou octobre. Une tenue du
     7 septembre 2026 relève-t-elle de 5786 ou de 5787 ? Le calcul
     ci-dessous ignore la question et ajoute 3760 à l'année civile,
     ce qui donne le résultat des documents fournis. À confirmer par
     le Rite avant toute impression officielle.                       */
export function avl(anneeVulgaire) {
  return anneeVulgaire + 3760;
}

/* ── La pierre plate du Tronc de la Veuve ───────────────────────────
   Source : Souverain Grand Commandeur — en maçonnerie, le kilogramme
   vaut l'euro et le gramme vaut le centime. La formule est : « le Tronc
   de la Veuve est alourdi d'une pierre plate de… ».

   Les grammes ne sont écrits que s'il y en a : « 87 kg » se lit mieux
   que « 87 kg 0 ». Et ils sont écrits sur trois chiffres, parce que
   50 centimes font 500 grammes, non 50.                              */
export function pierrePlate(montantEuros) {
  const centimes = Math.round(montantEuros * 100);
  const kg = Math.floor(centimes / 100);
  const g  = centimes % 100;
  if (g === 0) return `${kg} kg`;
  return `${kg} kg ${String(g * 10).padStart(3, '0')}`;
}

/* ── Le mois maçonnique ─────────────────────────────────────────────
   Source : planche à tracer, « le xxx ème mois de l'AVL ».
   ► NON CONFIRMÉ : l'usage le plus répandu fait commencer l'année en
     mars, ce qui place septembre au septième rang. À valider par le
     Rite avant tout usage en production.                             */
export function moisMaconnique(date) {
  return ((date.getMonth() + 12 - 2) % 12) + 1;   // mars = 1
}

/* ── Les ordinaux ───────────────────────────────────────────────────
   « le septième jour du septième mois ». Au-delà de trente-et-un, un
   jour de mois n'existe pas : la table s'arrête là.                  */
const ORDINAUX = [
  null, 'premier', 'deuxième', 'troisième', 'quatrième', 'cinquième',
  'sixième', 'septième', 'huitième', 'neuvième', 'dixième', 'onzième',
  'douzième', 'treizième', 'quatorzième', 'quinzième', 'seizième',
  'dix-septième', 'dix-huitième', 'dix-neuvième', 'vingtième',
  'vingt-et-unième', 'vingt-deuxième', 'vingt-troisième', 'vingt-quatrième',
  'vingt-cinquième', 'vingt-sixième', 'vingt-septième', 'vingt-huitième',
  'vingt-neuvième', 'trentième', 'trente-et-unième'
];
export function ordinal(n) {
  return ORDINAUX[n] ?? String(n);
}

/* ── Le degré, dit comme le Rite le dit ─────────────────────────────
   Source : Souverain Grand Commandeur — Apprenti Oved, Compagnon
   Boneh, Maître Adon. Les noms ne sont pas écrits ici : ils viennent
   de la table nomenclature_degres, pour que les degrés 4 à 33 puissent
   être nommés sans toucher au code.                                  */
export function degrePhrase(rang, nomDuDegre) {
  return `au ${ordinal(rang)} degré de ${nomDuDegre} du Rite Brith Israël`;
}

/* ── La date en toutes lettres ──────────────────────────────────────
   Source : convocation, « Lundi 7 Septembre 2026 ».                  */
export function dateLongue(date) {
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  }).format(date);
}

/* ── La qualité d'un membre, telle qu'elle s'imprime ────────────────
   Source : Souverain Grand Commandeur — « Maître Adon du RBI »,
   « Compagnon Boneh du RBI », « Apprenti Oved du RBI ».

   Le nom du degré vient de la table nomenclature_degres ; seule la
   forme de la phrase est ici. Un Frère qui n'a pas encore de degré du
   Rite garde la qualité acquise dans son rite d'origine, telle qu'elle
   est enregistrée dans qualifications_externes.                       */
export function qualite(nomDuDegre, { abrege = false } = {}) {
  return `${nomDuDegre} du ${abrege ? 'R∴B∴I∴' : 'Rite Brith Israël'}`;
}
