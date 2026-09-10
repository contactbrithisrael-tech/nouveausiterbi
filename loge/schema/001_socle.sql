-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 001 : SOCLE D'IDENTITÉ
--
--  Trois idées structurent ce fichier, et elles ne sont pas
--  interchangeables :
--
--  1. Une personne existe une seule fois. Elle n'appartient pas à une
--     loge : elle y est AFFILIÉE, pour une période donnée. Un Frère
--     affilié à deux ateliers, ou qui change de loge, ne doit pas
--     exister en double — sinon ses degrés, ses capitations et son
--     historique se dédoublent avec lui.
--
--  2. Les degrés appartiennent au Rite, pas à la loge. Un 4e reste 4e
--     s'il change d'atelier. Ils sont donc rattachés à la personne.
--
--  3. Les offices appartiennent à la loge ET à l'année. « Vénérable »
--     n'est pas une propriété d'un Frère, c'est une charge exercée
--     dans un atelier pendant un mandat. C'est cette table qui
--     donnera plus tard les droits d'accès au logiciel.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── Les ateliers ───────────────────────────────────────────────────
-- Loges bleues, ateliers de perfection, et l'Obédience elle-même
-- (enregistrée comme un atelier de type « obedience » pour porter les
-- membres qui n'appartiennent à aucune loge : dignitaires, membres
-- directs du Grand Collège).
CREATE TABLE loges (
  id            INTEGER PRIMARY KEY,
  nom           TEXT    NOT NULL,          -- « Loge Israël Darmon n°1 »
  numero        INTEGER,                   -- numéro au tableau de l'Obédience
  type          TEXT    NOT NULL,          -- symbolique | perfection | obedience
  orient        TEXT,                      -- ville : « Paris », « Marseille »
  degres_min    INTEGER NOT NULL DEFAULT 1,-- degrés travaillés dans l'atelier
  degres_max    INTEGER NOT NULL DEFAULT 3,
  date_creation TEXT,                      -- ISO-8601 : « 2025-03-21 »
  date_mise_en_sommeil TEXT,               -- NULL tant que l'atelier travaille
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (type IN ('symbolique','perfection','obedience')),
  CHECK (degres_min >= 1 AND degres_max <= 33 AND degres_min <= degres_max)
);

-- ── Les personnes ──────────────────────────────────────────────────
-- Membres ET profanes en instance. Un candidat entre ici dès sa
-- demande : son parcours (enquêtes, tuilage, vote) se suit ensuite
-- sans ressaisie le jour de son initiation.
--
-- ATTENTION RGPD : cette table est le fichier lui-même. Toute colonne
-- ajoutée ici doit répondre à « à quoi sert-elle concrètement ? ».
-- Rien de ce qui n'est pas utilisé ne doit y figurer.
CREATE TABLE membres (
  id            INTEGER PRIMARY KEY,
  nom           TEXT    NOT NULL,
  prenoms       TEXT    NOT NULL,
  nom_initiatique TEXT,                    -- si le Rite en attribue un
  email         TEXT,                      -- unique : sert d'identifiant
  telephone     TEXT,
  date_naissance TEXT,                     -- utile pour l'âge à l'initiation
  ville         TEXT,                      -- ville seule : l'adresse postale
  code_postal   TEXT,                      -- complète n'est utile qu'au
  adresse       TEXT,                      -- Secrétaire, et reste optionnelle
  profession    TEXT,
  photo_cle     TEXT,                      -- clé de l'objet dans R2, jamais
                                           -- l'image en base
  statut        TEXT    NOT NULL DEFAULT 'candidat',
  date_deces    TEXT,
  notes         TEXT,                      -- champ libre du Secrétaire
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  modifie_le    TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (statut IN (
    'candidat',     -- profane en instance, pas encore initié
    'actif',        -- membre à jour, participe aux travaux
    'sommeil',      -- membre en sommeil, ne convoquer que sur demande
    'honoraire',    -- membre d'honneur, exempté de capitation
    'demission',    -- a démissionné
    'radiation',    -- radié
    'decede'
  ))
);

CREATE UNIQUE INDEX idx_membres_email ON membres(email) WHERE email IS NOT NULL;
CREATE INDEX idx_membres_statut ON membres(statut);
CREATE INDEX idx_membres_nom ON membres(nom, prenoms);

-- ── Les affiliations ───────────────────────────────────────────────
-- Le lien entre une personne et un atelier, daté. C'est cette table,
-- et non « membres », qui répond à « qui convoquer le 12 mars ? » :
-- on interroge les affiliations ouvertes à cette date.
--
-- Une ligne par période. Un Frère qui quitte une loge puis y revient
-- a deux lignes, pas une ligne modifiée : l'historique de la loge ne
-- doit jamais être réécrit.
CREATE TABLE affiliations (
  id            INTEGER PRIMARY KEY,
  membre_id     INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  mode          TEXT    NOT NULL,          -- comment il est entré dans l'atelier
  date_debut    TEXT    NOT NULL,
  date_fin      TEXT,                      -- NULL = affiliation en cours
  motif_fin     TEXT,                      -- démission, radiation, transfert…
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (mode IN ('initiation','affiliation','regularisation','fondateur')),
  CHECK (date_fin IS NULL OR date_fin >= date_debut)
);

CREATE INDEX idx_affiliations_loge ON affiliations(loge_id, date_fin);
CREATE INDEX idx_affiliations_membre ON affiliations(membre_id);

-- ── Les degrés ─────────────────────────────────────────────────────
-- Rattachés à la personne, pas à l'atelier : un 4e reste 4e s'il
-- change de loge. « loge_id » n'enregistre que le lieu où le degré a
-- été conféré, pour la planche et pour le certificat.
--
-- Aucune ligne n'est jamais supprimée ni modifiée : un degré conféré
-- est un fait daté. Une erreur de saisie se corrige par une ligne
-- d'annulation, pas par un UPDATE.
CREATE TABLE degres (
  id            INTEGER PRIMARY KEY,
  membre_id     INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  degre         INTEGER NOT NULL,          -- 1 à 33
  date          TEXT    NOT NULL,
  loge_id       INTEGER REFERENCES loges(id),
  tenue_id      INTEGER,                   -- renseigné en phase 2 (tenues)
  mode          TEXT    NOT NULL DEFAULT 'confere',
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (degre BETWEEN 1 AND 33),
  CHECK (mode IN ('confere','communique','regularise','honoris'))
);

CREATE UNIQUE INDEX idx_degres_unique ON degres(membre_id, degre);
CREATE INDEX idx_degres_date ON degres(date);

-- ── Les offices ────────────────────────────────────────────────────
-- Une charge, dans un atelier, pendant un mandat. C'est d'ici que
-- viendront les droits du logiciel : le Trésorier en exercice voit la
-- comptabilité, son prédécesseur ne la voit plus le lendemain de la
-- passation. Aucun droit n'est accordé « à une personne ».
-- Les charges existantes, que le Rite complète lui-même. Elles ne sont
-- PAS une liste figée dans une contrainte SQL : ajouter un office ne
-- doit demander ni développeur ni migration, seulement une ligne ici.
--
-- « rang » donne l'ordre protocolaire : c'est celui dans lequel les
-- Officiers apparaissent au tableau des présents de la planche.
-- « signe_planche » désigne les trois qui la signent — d'après votre
-- modèle : le Vénérable Maître, l'Orateur, le Secrétaire.
CREATE TABLE offices_types (
  code          TEXT    PRIMARY KEY,       -- 'venerable'
  libelle       TEXT    NOT NULL,          -- 'Vénérable Maître'
  abreviation   TEXT,                      -- 'VM∴'
  rang          INTEGER NOT NULL DEFAULT 99,
  signe_planche INTEGER NOT NULL DEFAULT 0,
  actif         INTEGER NOT NULL DEFAULT 1,
  CHECK (signe_planche IN (0,1) AND actif IN (0,1))
);

-- Les trois Offices de la Loge, et trois seulement. Constitution V9,
-- article 9quater : « Chaque Loge est dirigée par trois Officiers, et
-- trois seulement ». Ils forment le Collège des Trois Lumières
-- (שלוש האורות — Shalosh HaOrot).
--
-- ► CE QUE LA CONSTITUTION EXCLUT EXPRESSÉMENT : « pas de Grand
--   Hospitalier en Loge (fonction au niveau du Suprême Conseil), pas
--   d'Orateur distinct (le 1er Surveillant assume cette fonction), pas
--   de Secrétaire distinct (PV tenus par rotation), pas de Trésorier
--   distinct ». J'avais d'abord semé douze charges tirées de l'usage
--   maçonnique courant : elles n'existent pas dans ce Rite.
--
-- ► Les charges du SUPRÊME CONSEIL — Grand Secrétaire, Grand Trésorier,
--   Grand Chancelier, Grand Orateur, Grand Expert, Grand Hospitalier —
--   sont d'un autre ordre : elles s'attachent à l'atelier de type
--   « obedience », pas à une loge symbolique.
INSERT INTO offices_types (code, libelle, abreviation, rang, signe_planche) VALUES
  ('venerable',           'Vénérable Maître',    'VM∴',       1, 1),
  ('premier_surveillant', 'Premier Surveillant', '1er Surv∴', 2, 1),
  ('second_surveillant',  'Second Surveillant',  '2d Surv∴',  3, 1);

-- Charges du Suprême Conseil, distinctes de celles des Loges.
INSERT INTO offices_types (code, libelle, abreviation, rang, signe_planche) VALUES
  ('sgc',              'Souverain Grand Commandeur',        'SGC∴',   10, 0),
  ('lt_sgc',           'Lieutenant Souverain Grand Commandeur','LtSGC∴',11, 0),
  ('grand_maitre_adj', 'Grand Maître Adjoint',              'GMA∴',   12, 0),
  ('assistant_gm',     'Assistant Grand Maître',            'AGM∴',   13, 0),
  ('grand_secretaire', 'Grand Secrétaire',                  'GSecr∴', 14, 0),
  ('grand_tresorier',  'Grand Trésorier',                   'GTrés∴', 15, 0),
  ('grand_chancelier', 'Grand Chancelier',                  'GChanc∴',16, 0),
  ('grand_orateur',    'Grand Orateur',                     'GOr∴',   17, 0),
  ('grand_expert',     'Grand Expert',                      'GExp∴',  18, 0),
  ('grand_hospitalier','Grand Hospitalier',                 'GHosp∴', 19, 0),
  ('grand_mc',         'Grand Maître des Cérémonies',       'GMC∴',   20, 0);

CREATE TABLE offices (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  membre_id     INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  office        TEXT    NOT NULL REFERENCES offices_types(code),
  date_debut    TEXT    NOT NULL,
  date_fin      TEXT,                      -- NULL = office en cours
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (date_fin IS NULL OR date_fin >= date_debut)
);

CREATE INDEX idx_offices_loge ON offices(loge_id, date_fin);
CREATE INDEX idx_offices_membre ON offices(membre_id, date_fin);

-- Un seul titulaire par office et par atelier à un instant donné.
-- SQLite ne sait pas exprimer cette contrainte sur des intervalles :
-- elle est vérifiée par l'API avant insertion (functions/api/offices).
