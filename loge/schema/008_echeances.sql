-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 008 : ÉCHÉANCIERS ET DROITS D'ACTE
--
--  Le barème du Rite : 25 € par tenue, une tenue par mois, du 1er
--  janvier au 31 décembre. Ce n'est pas une capitation annuelle qu'on
--  règle en une fois : c'est un montant récurrent, et le Trésorier a
--  besoin de savoir non pas « qui doit », mais « qui doit QUOI ce
--  mois-ci ».
--
--  Les agapes n'entrent pas ici. Elles se paient à la tenue, seulement
--  par ceux qui viennent, et leur prix change avec le traiteur — c'est
--  la table « agapes » de la migration 003 qui les porte.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── Les échéances ──────────────────────────────────────────────────
-- Le découpage d'un appel dans le temps. Douze lignes de 25 € pour une
-- année civile, ou une seule ligne si la loge décide un règlement
-- unique : c'est une donnée, pas une version du logiciel.
--
-- Un règlement se rattache à l'appel, pas à l'échéance : un membre qui
-- verse 100 € couvre quatre mois sans qu'on ait à découper son
-- virement. L'imputation se calcule, du plus ancien au plus récent.
CREATE TABLE appel_echeances (
  id            INTEGER PRIMARY KEY,
  appel_id      INTEGER NOT NULL REFERENCES appels_capitation(id) ON DELETE CASCADE,
  rang          INTEGER NOT NULL,
  libelle       TEXT    NOT NULL,          -- « Tenue de mars »
  montant       REAL    NOT NULL,
  date_echeance TEXT    NOT NULL,
  tenue_id      INTEGER REFERENCES tenues(id) ON DELETE SET NULL,
  CHECK (montant > 0)
);

CREATE UNIQUE INDEX idx_echeances_rang ON appel_echeances(appel_id, rang);
CREATE INDEX idx_echeances_date ON appel_echeances(date_echeance);

-- ── Les droits d'acte ──────────────────────────────────────────────
-- Initiation, adhésion, affiliation, élévation : 150 €. Ce sont des
-- droits ponctuels, dus une fois, à l'occasion d'un acte — jamais des
-- lignes de capitation, sans quoi ils reviendraient chaque année.
--
-- Le tarif est rattaché à l'exercice : il peut changer d'une année sur
-- l'autre sans réécrire les droits déjà appelés.
CREATE TABLE tarifs_actes (
  id            INTEGER PRIMARY KEY,
  exercice_id   INTEGER NOT NULL REFERENCES exercices(id) ON DELETE CASCADE,
  acte          TEXT    NOT NULL,
  montant       REAL    NOT NULL,
  CHECK (montant >= 0),
  CHECK (acte IN ('initiation','adhesion','affiliation','passage','elevation',
                  'installation','duplicata_diplome'))
);

CREATE UNIQUE INDEX idx_tarifs_acte ON tarifs_actes(exercice_id, acte);

-- ── Les droits dus ─────────────────────────────────────────────────
-- Le montant est RECOPIÉ depuis le tarif au moment où le droit est
-- appelé, pour la même raison que les lignes d'appel : une hausse du
-- tarif ne doit pas réécrire ce qu'un Frère devait l'an dernier.
CREATE TABLE droits_dus (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  membre_id     INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  exercice_id   INTEGER NOT NULL REFERENCES exercices(id),
  acte          TEXT    NOT NULL,
  montant       REAL    NOT NULL,
  tenue_id      INTEGER REFERENCES tenues(id) ON DELETE SET NULL,
  date_appel    TEXT    NOT NULL,
  statut        TEXT    NOT NULL DEFAULT 'du',
  motif_remise  TEXT,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (montant >= 0),
  CHECK (statut IN ('du','solde','remis','annule')),
  CHECK ((statut = 'remis') = (motif_remise IS NOT NULL))
);

CREATE INDEX idx_droits_membre ON droits_dus(membre_id);
CREATE INDEX idx_droits_exercice ON droits_dus(exercice_id, statut);
