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
   Source : planche à tracer de Bereshit, « l'AVL 6025 » pour 2025.
   L'année vulgaire plus quatre mille.                                */
export function avl(anneeVulgaire) {
  return anneeVulgaire + 4000;
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
