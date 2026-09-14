-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 007 : EXERCICES, CAPITATIONS ET APPELS
--
--  Deux principes de tenue de comptes sont inscrits ici, et ils
--  valent plus que tout le reste du fichier :
--
--  1. L'EXERCICE EST UNE DONNÉE, PAS UNE STRUCTURE. Année civile ou
--     année maçonnique de septembre à juin : ce sont deux dates dans
--     une ligne, pas deux versions du logiciel. Vous trancherez en
--     saisissant, pas en me le demandant.
--
--  2. UN APPEL ÉMIS NE BOUGE PLUS. Les lignes du barème sont RECOPIÉES
--     dans l'appel au moment de son émission. Si la capitation
--     augmente l'année suivante, les appels déjà émis gardent leur
--     montant — sans quoi le relevé d'un membre changerait sous ses
--     yeux, et les impayés de l'an dernier se recalculeraient tout
--     seuls au tarif de cette année.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── Les exercices ──────────────────────────────────────────────────
-- Un exercice clos ne se modifie plus : c'est ce qui donne sa valeur
-- au bilan présenté en assemblée.
CREATE TABLE exercices (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  libelle       TEXT    NOT NULL,          -- « 2026-2027 »
  date_debut    TEXT    NOT NULL,
  date_fin      TEXT    NOT NULL,
  statut        TEXT    NOT NULL DEFAULT 'ouvert',
  clos_le       TEXT,
  clos_par      INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (statut IN ('ouvert','clos')),
  CHECK (date_fin > date_debut),
  CHECK ((statut = 'clos') = (clos_le IS NOT NULL))
);

CREATE UNIQUE INDEX idx_exercices_libelle ON exercices(loge_id, libelle);

-- ── Le barème ──────────────────────────────────────────────────────
-- Une ligne par part : la part de l'Obédience, celle de la Loge, le
-- Tronc, une assurance… Le montant total n'est pas stocké, il est la
-- somme des lignes.
--
-- « destinataire » sert à la remontée vers l'Obédience : le Trésorier
-- sait à tout moment ce qu'il doit reverser, sans le recalculer.
CREATE TABLE bareme_lignes (
  id            INTEGER PRIMARY KEY,
  exercice_id   INTEGER NOT NULL REFERENCES exercices(id) ON DELETE CASCADE,
  rang          INTEGER NOT NULL,
  libelle       TEXT    NOT NULL,          -- « Capitation Obédience »
  montant       REAL    NOT NULL,
  destinataire  TEXT    NOT NULL DEFAULT 'loge',
  applicable_a  TEXT    NOT NULL DEFAULT 'actifs',
  CHECK (montant >= 0),
  CHECK (destinataire IN ('obedience','loge','tronc','autre')),
  CHECK (applicable_a IN ('tous','actifs','actifs_et_sommeil'))
);

CREATE UNIQUE INDEX idx_bareme_rang ON bareme_lignes(exercice_id, rang);

-- ── Les appels ─────────────────────────────────────────────────────
-- Un par membre et par exercice. « exonere » existe pour les membres
-- honoraires : il vaut mieux un appel exonéré et daté qu'un membre
-- absent du rôle, qu'on finit par oublier de compter.
CREATE TABLE appels_capitation (
  id            INTEGER PRIMARY KEY,
  exercice_id   INTEGER NOT NULL REFERENCES exercices(id) ON DELETE CASCADE,
  membre_id     INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  date_emission TEXT    NOT NULL,
  date_echeance TEXT,
  statut        TEXT    NOT NULL DEFAULT 'emis',
  motif_exoneration TEXT,
  note          TEXT,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (statut IN ('emis','exonere','annule')),
  CHECK ((statut = 'exonere') = (motif_exoneration IS NOT NULL))
);

CREATE UNIQUE INDEX idx_appels_membre ON appels_capitation(exercice_id, membre_id);
CREATE INDEX idx_appels_statut ON appels_capitation(statut);

-- ── Les lignes de l'appel ──────────────────────────────────────────
-- La copie du barème au jour de l'émission. C'est cette copie qui fait
-- foi, jamais le barème lui-même.
CREATE TABLE appel_lignes (
  id            INTEGER PRIMARY KEY,
  appel_id      INTEGER NOT NULL REFERENCES appels_capitation(id) ON DELETE CASCADE,
  rang          INTEGER NOT NULL,
  libelle       TEXT    NOT NULL,
  montant       REAL    NOT NULL,
  destinataire  TEXT    NOT NULL,
  CHECK (montant >= 0),
  CHECK (destinataire IN ('obedience','loge','tronc','autre'))
);

CREATE UNIQUE INDEX idx_appel_lignes_rang ON appel_lignes(appel_id, rang);

-- ── Les règlements ─────────────────────────────────────────────────
-- Tout ce qui rentre : capitations, triangles d'agapes, dons.
--
-- « mode » enregistre COMMENT on a encaissé, y compris SumUp au
-- lecteur de carte le soir de la tenue et HelloAsso en ligne. Le
-- logiciel n'appelle aucun de ces services : il enregistre le fait et
-- garde la référence, ce qui suffit à rapprocher un relevé. Brancher
-- une interface de paiement pour une trentaine de règlements par an
-- coûterait plus cher à maintenir que la saisie qu'elle évite.
--
-- Un règlement peut être partiel : rien n'oblige à solder un appel en
-- une fois. Le solde n'est stocké nulle part, il se calcule.
CREATE TABLE reglements (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  membre_id     INTEGER REFERENCES membres(id) ON DELETE SET NULL,
  appel_id      INTEGER REFERENCES appels_capitation(id) ON DELETE SET NULL,
  tenue_id      INTEGER REFERENCES tenues(id) ON DELETE SET NULL,
  motif         TEXT    NOT NULL,
  montant       REAL    NOT NULL,
  date          TEXT    NOT NULL,
  mode          TEXT    NOT NULL,
  reference     TEXT,                      -- n° de chèque, référence SumUp
                                           -- ou HelloAsso, pour le rapprochement
  encaisse_par  INTEGER REFERENCES membres(id) ON DELETE SET NULL,
  saisi_par     INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (montant > 0),
  CHECK (motif IN ('capitation','agapes','don','visite','autre')),
  CHECK (mode IN ('especes','cheque','virement','sumup','helloasso','autre')),
  -- Un règlement de capitation se rattache à un appel ; un triangle
  -- d'agapes se rattache à une tenue.
  CHECK (motif <> 'capitation' OR appel_id IS NOT NULL),
  CHECK (motif <> 'agapes' OR tenue_id IS NOT NULL)
);

CREATE INDEX idx_reglements_appel ON reglements(appel_id);
CREATE INDEX idx_reglements_membre ON reglements(membre_id, date);
CREATE INDEX idx_reglements_loge ON reglements(loge_id, date);

-- ── Le livre de caisse ─────────────────────────────────────────────
-- Pas de partie double, pas de plan comptable, pas de classe 6 : des
-- recettes et des dépenses, ventilées par poste. C'est ce qu'un
-- Trésorier de loge tient réellement, et cela suffit à produire le
-- compte de résultat de l'assemblée.
--
-- Les règlements ci-dessus ne sont PAS recopiés ici : la vue finale
-- additionne les deux sources. Une recette saisie deux fois est une
-- recette comptée deux fois.
CREATE TABLE postes (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  sens          TEXT    NOT NULL,
  libelle       TEXT    NOT NULL,          -- « Location du Temple », « Traiteur »
  rang          INTEGER NOT NULL DEFAULT 0,
  actif         INTEGER NOT NULL DEFAULT 1,
  CHECK (sens IN ('recette','depense')),
  CHECK (actif IN (0,1))
);

CREATE UNIQUE INDEX idx_postes_libelle ON postes(loge_id, sens, libelle);

CREATE TABLE mouvements (
  id            INTEGER PRIMARY KEY,
  exercice_id   INTEGER NOT NULL REFERENCES exercices(id) ON DELETE CASCADE,
  poste_id      INTEGER NOT NULL REFERENCES postes(id),
  date          TEXT    NOT NULL,
  libelle       TEXT    NOT NULL,
  montant       REAL    NOT NULL,
  mode          TEXT    NOT NULL DEFAULT 'virement',
  piece         TEXT,                      -- référence de la facture
  saisi_par     INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (montant > 0),
  CHECK (mode IN ('especes','cheque','virement','sumup','helloasso','autre'))
);

CREATE INDEX idx_mouvements_exercice ON mouvements(exercice_id, date);

-- ── Ce que le Trésorier regarde vraiment ───────────────────────────
-- Le solde de chaque appel, sans qu'aucun solde n'ait été stocké.
CREATE VIEW soldes_capitation AS
SELECT a.id AS appel_id, a.exercice_id, a.membre_id, a.statut,
       ROUND(COALESCE((SELECT SUM(montant) FROM appel_lignes
                       WHERE appel_id = a.id), 0), 2) AS du,
       ROUND(COALESCE((SELECT SUM(montant) FROM reglements
                       WHERE appel_id = a.id), 0), 2) AS regle,
       ROUND(COALESCE((SELECT SUM(montant) FROM appel_lignes
                       WHERE appel_id = a.id), 0)
           - COALESCE((SELECT SUM(montant) FROM reglements
                       WHERE appel_id = a.id), 0), 2) AS reste
FROM appels_capitation a
WHERE a.statut = 'emis';
