-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 005 : TRONC DE LA VEUVE ET LOGES AMIES
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── Le Tronc de la Veuve ───────────────────────────────────────────
-- Deux sens, un seul registre : ce qui entre en tenue, ce qui sort en
-- secours. Le solde n'est pas stocké, il se calcule — un solde recopié
-- est un solde qui finit par diverger de ses mouvements.
--
-- ► DONNÉE SENSIBLE. Le montant d'une collecte est un fait de loge et
--   figure dans la planche à tracer. L'identité de celui qui reçoit un
--   secours ne l'est pas : c'est la donnée la plus sensible de tout ce
--   logiciel. « beneficiaire » est donc facultatif, visible du seul
--   Hospitalier, et destiné à rester vide dans le cas ordinaire — une
--   référence connue de lui suffit à la tenue de ses comptes.
--
-- ► La planche à tracer fournie écrit le contenu du Tronc sous forme
--   rituelle, « alourdi d'une pierre plate de X kg ». Le registre tient
--   des euros ; c'est l'impression qui transpose. Reste à confirmer que
--   les kilogrammes de la planche sont bien les euros du registre.
CREATE TABLE tronc_mouvements (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  tenue_id      INTEGER REFERENCES tenues(id) ON DELETE SET NULL,
  sens          TEXT    NOT NULL,
  montant       REAL    NOT NULL,          -- toujours positif ; « sens » décide
  date          TEXT    NOT NULL,
  detenteur     INTEGER REFERENCES membres(id) ON DELETE SET NULL,
                                           -- l'Hospitalier, ou le Frère
                                           -- faisant fonction ce soir-là
  beneficiaire  TEXT,                      -- laisser vide dans le cas ordinaire
  decide_le     TEXT,                      -- date de la décision de secours
  motif         TEXT,
  saisi_par     INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (sens IN ('collecte','secours','versement_solidarite','regularisation')),
  CHECK (montant > 0),
  -- Un secours suppose une décision ; une collecte suppose une tenue.
  CHECK (sens <> 'secours' OR decide_le IS NOT NULL),
  CHECK (sens <> 'collecte' OR tenue_id IS NOT NULL)
);

CREATE INDEX idx_tronc_loge ON tronc_mouvements(loge_id, date);
CREATE INDEX idx_tronc_tenue ON tronc_mouvements(tenue_id);

-- Le solde du Tronc, à tout instant, sans jamais l'avoir stocké.
CREATE VIEW tronc_solde AS
SELECT loge_id,
       ROUND(SUM(CASE WHEN sens IN ('collecte','regularisation')
                      THEN montant ELSE -montant END), 2) AS solde,
       COUNT(*) AS mouvements,
       MAX(date) AS dernier_mouvement
FROM tronc_mouvements
GROUP BY loge_id;

-- ── Les obédiences amies ───────────────────────────────────────────
-- Un traité se signe avec une obédience, pas avec un atelier : le
-- traité type que vous m'avez transmis ne demande que le nom de
-- l'obédience, son représentant et sa fonction. C'est donc ce niveau
-- qui porte le traité, et le niveau du dessous qui porte les visites.
CREATE TABLE obediences_amies (
  id            INTEGER PRIMARY KEY,
  nom           TEXT    NOT NULL,          -- « Fédération de Loges
                                           --   Traditionnelles et Souveraines »
  sigle         TEXT,                      -- « F.L.T.S. »
  pays          TEXT,
  representant_nom      TEXT,              -- « TIF Thierry HUGON — 33ème »
  representant_fonction TEXT,              -- « Président »
  acte_type     TEXT,                      -- traité, lettre d'amitié…
  acte_date     TEXT,
  acte_lieu     TEXT,                      -- « Ventabren »
  acte_fichier_cle TEXT,                   -- le PDF signé, dans R2
  statut        TEXT    NOT NULL DEFAULT 'en_vigueur',
  notes         TEXT,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (acte_type IS NULL OR acte_type IN
         ('traite_amitie','lettre_amitie','reconnaissance_mutuelle','patente')),
  CHECK (statut IN ('en_projet','en_vigueur','suspendu','denonce'))
);

-- ── Les ateliers amis ──────────────────────────────────────────────
-- Le carnet d'adresses des loges qu'on visite. « obedience_amie_id »
-- peut rester vide : toutes les loges amies ne relèvent pas d'une
-- obédience avec laquelle un traité a été signé.
CREATE TABLE loges_amies (
  id            INTEGER PRIMARY KEY,
  obedience_amie_id INTEGER REFERENCES obediences_amies(id) ON DELETE SET NULL,
  nom           TEXT    NOT NULL,
  numero        TEXT,
  orient        TEXT,
  rite          TEXT,
  ville         TEXT,
  adresse_temple TEXT,
  contact_nom   TEXT,
  contact_email TEXT,
  actif         INTEGER NOT NULL DEFAULT 1,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (actif IN (0,1))
);

CREATE INDEX idx_loges_amies_obedience ON loges_amies(obedience_amie_id);

-- ── L'agenda des loges amies ───────────────────────────────────────
-- Le traité FLTS le prévoit noir sur blanc : « chaque Atelier pourra
-- transmettre les plannings de ses Travaux (avec les adresses des
-- Loges) ». Cette table est ce planning reçu, et la suivante ce que
-- les Frères et Sœurs en font.
CREATE TABLE tenues_amies (
  id            INTEGER PRIMARY KEY,
  loge_amie_id  INTEGER NOT NULL REFERENCES loges_amies(id) ON DELETE CASCADE,
  date          TEXT    NOT NULL,
  heure         TEXT,
  degre         INTEGER,
  intitule      TEXT,                      -- « Tenue d'installation »
  sujet         TEXT,                      -- le travail annoncé
  lieu          TEXT,
  tuilage_requis INTEGER NOT NULL DEFAULT 1,
  recu_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (tuilage_requis IN (0,1))
);

CREATE INDEX idx_tenues_amies_date ON tenues_amies(date);

-- ── Les visites ────────────────────────────────────────────────────
-- Qui souhaite y aller, qui s'est inscrit, qui y est allé. C'est aussi
-- ce qui permet de répondre au Vénérable quand il demande « qui de
-- l'Atelier a visité la FLTS cette année ? ».
CREATE TABLE visites (
  id            INTEGER PRIMARY KEY,
  tenue_amie_id INTEGER NOT NULL REFERENCES tenues_amies(id) ON DELETE CASCADE,
  membre_id     INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  statut        TEXT    NOT NULL DEFAULT 'souhaitee',
  annonce_le    TEXT,                      -- date où la loge amie a été prévenue
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (statut IN ('souhaitee','annoncee','effectuee','annulee'))
);

CREATE UNIQUE INDEX idx_visites_unique ON visites(tenue_amie_id, membre_id);
CREATE INDEX idx_visites_membre ON visites(membre_id);
