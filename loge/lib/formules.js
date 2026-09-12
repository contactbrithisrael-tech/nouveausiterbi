/* ═══════════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — formules.js

   Les règles d'écriture propres au Rite, réunies ici et nulle part
   ailleurs. Chacune est appliquée à un seul endroit : le jour où l'une
   d'elles change, elle change une fois.

   Aucune de ces règles n'est inventée. Elles viennent des documents de
   la R∴L∴ Bereshit ou du Souverain Grand Commandeur, et la source est
   citée à chaque fois.
════════════════════════════════════════════════════════════════════ */

/* ── La date hébraïque ──────────────────────────────────────────────
   Source : Constitution V9, « L'An de la Vraie Lumière 5786 (2026 de
   l'ère vulgaire) », et décision du Souverain Grand Commandeur — on
   garde l'année hébraïque ET l'année civile, et l'on porte les deux
   dates sur les documents.

   ► J'avais d'abord écrit « année vulgaire + 3760 ». C'était faux dès
     l'automne : l'année hébraïque tourne à Roch Hachana, non au 1er
     janvier. Le 7 septembre 2026 est bien en 5786, mais le 5 octobre
     2026 est déjà en 5787 — et le calcul par addition l'aurait daté
     5786 sur la planche à tracer.

   ► Le calendrier hébraïque est connu du navigateur. On le lui demande
     plutôt que de le réimplémenter : il sait les mois embolismiques,
     les années défectives et abondantes, et la date de Roch Hachana
     pour chaque année.                                                */
const MOIS_HEBREUX_MAJ = t => t.replace(/(^|\s)(\p{Ll})/gu, (m, e, l) => e + l.toUpperCase());

export function dateHebraique(date) {
  const t = new Intl.DateTimeFormat('fr-u-ca-hebrew',
    { day: 'numeric', month: 'long', year: 'numeric' }).format(date);
  return MOIS_HEBREUX_MAJ(t.replace(/\s*A\.?\s*M\.?\s*$/, '').trim());
}

export function anneeHebraique(date) {
  return Number(new Intl.DateTimeFormat('en-u-ca-hebrew',
    { year: 'numeric' }).format(date).replace(/\D/g, ''));
}

/* Les deux dates, comme le Rite les veut désormais. */
export function doubleDate(date) {
  return `${dateHebraique(date)} — ${dateLongue(date)}`;
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
   être nommés sans toucher au code.

   ► « au premier degré D'APPRENTI Oved », et non « de l'Apprenti » :
     après « degré », le nom du grade suit sans article, avec son
     élision devant voyelle.                                          */
export function degrePhrase(rang, nomDuDegre) {
  const de = /^[aeiouyéèêàâîôûAEIOUY]/.test(nomDuDegre) ? "d'" : 'de ';
  return `au ${ordinal(rang)} degré ${de}${nomDuDegre} du Rite Brith Israël`;
}

/* La forme brève, pour une fiche, un diplôme ou un certificat :
   « Oved — 1er degré du Rite Brith Israël ».                         */
export function degreBref(rang, nomHebreu) {
  return `${nomHebreu} — ${rang}${rang === 1 ? 'er' : 'e'} degré du Rite Brith Israël`;
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
