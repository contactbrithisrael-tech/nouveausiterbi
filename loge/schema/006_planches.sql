-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 006 : LA PLANCHE À TRACER
--
--  Le modèle fourni est une planche du REAA dont seul l'en-tête avait
--  été changé : le corps y désigne encore une loge d'une autre
--  obédience et des travaux ouverts à un autre rite. Ce schéma
--  transpose la FORME au Rite Brith Israël et supprime la cause de
--  l'erreur — ce qui était recopié à la main devient calculé.
--
--  La planche se compose de trois matières, et il est essentiel de ne
--  pas les mélanger :
--
--  1. CE QUI SE CALCULE — la date, l'année de Vraie Lumière, le nom et
--     le numéro de l'atelier, l'orient, les présents avec leur qualité
--     et leur office, les excusés, les visiteurs, les travaux
--     présentés, le montant du Tronc, la date de la prochaine tenue.
--     Le Secrétaire n'en saisit rien. C'est déjà dans la base.
--
--  2. CE QUE LE SECRÉTAIRE ÉCRIT — le récit de ce qui s'est dit. Un
--     paragraphe par point de l'ordre du jour. Aucun automate ne
--     l'écrira à sa place : une archive de loge rédigée par une
--     machine serait une archive fausse.
--
--  3. LES FORMULES RITUELLES — invariables, portées par le gabarit
--     d'impression (loge/gabarits/planche-a-tracer.html), jamais
--     stockées ligne à ligne dans la base.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── La planche ─────────────────────────────────────────────────────
-- Une par tenue, jamais deux. Son parcours est celui de l'usage :
-- le Secrétaire la rédige, la soumet, elle est lue et approuvée à la
-- tenue SUIVANTE, puis archivée. « approuvee_en_tenue_id » enregistre
-- où elle l'a été : c'est ce qui donne sa valeur au document.
CREATE TABLE planches_tracees (
  id            INTEGER PRIMARY KEY,
  tenue_id      INTEGER NOT NULL UNIQUE REFERENCES tenues(id) ON DELETE CASCADE,

  -- Ce que seul le Secrétaire connaît et qui ne se déduit de rien.
  allocution    TEXT,                      -- l'accueil du Vénérable
  sac_propositions TEXT,                   -- « revient pur et sans attaches »,
                                           -- ou ce qui s'y trouvait
  tronc_montant REAL,                      -- recopié dans tronc_mouvements
  tronc_confie_a INTEGER REFERENCES membres(id) ON DELETE SET NULL,
  prochaine_tenue_id INTEGER REFERENCES tenues(id) ON DELETE SET NULL,
  observations  TEXT,

  redigee_par   INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  redigee_le    TEXT,
  soumise_le    TEXT,
  approuvee_en_tenue_id INTEGER REFERENCES tenues(id) ON DELETE SET NULL,
  approuvee_le  TEXT,
  fichier_cle   TEXT,                      -- le PDF signé et archivé, dans R2
  statut        TEXT    NOT NULL DEFAULT 'brouillon',
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (statut IN ('brouillon','soumise','approuvee','archivee')),
  -- Une planche approuvée l'a été quelque part, à une date.
  CHECK (statut <> 'approuvee' OR
         (approuvee_le IS NOT NULL AND approuvee_en_tenue_id IS NOT NULL)),
  -- Et jamais dans la tenue qu'elle relate : elle se lit à la suivante.
  CHECK (approuvee_en_tenue_id IS NULL OR approuvee_en_tenue_id <> tenue_id)
);

CREATE INDEX idx_planches_statut ON planches_tracees(statut);

-- ── Les paragraphes ────────────────────────────────────────────────
-- Le récit, point par point, dans l'ordre de l'ordre du jour.
-- « ordre_du_jour_id » relie le paragraphe au point qu'il relate : le
-- Secrétaire ouvre sa planche déjà découpée aux bons endroits, avec
-- les intitulés en place, et n'a plus qu'à écrire dessous.
CREATE TABLE planche_paragraphes (
  id            INTEGER PRIMARY KEY,
  planche_id    INTEGER NOT NULL REFERENCES planches_tracees(id) ON DELETE CASCADE,
  rang          INTEGER NOT NULL,
  ordre_du_jour_id INTEGER REFERENCES ordre_du_jour(id) ON DELETE SET NULL,
  intitule      TEXT,
  texte         TEXT    NOT NULL DEFAULT ''
);

CREATE UNIQUE INDEX idx_paragraphes_rang ON planche_paragraphes(planche_id, rang);

-- ── Les signatures ─────────────────────────────────────────────────
-- Le modèle fourni en porte trois : le Vénérable Maître, l'Orateur, le
-- Secrétaire. Elles sont manuscrites sur le document imprimé ; ce qui
-- est enregistré ici, c'est le fait que la planche a été signée, par
-- qui et quand — pas une image de signature.
CREATE TABLE planche_signatures (
  id            INTEGER PRIMARY KEY,
  planche_id    INTEGER NOT NULL REFERENCES planches_tracees(id) ON DELETE CASCADE,
  office        TEXT    NOT NULL REFERENCES offices_types(code),
  membre_id     INTEGER REFERENCES membres(id) ON DELETE SET NULL,
  signe_le      TEXT
  -- Quels offices signent n'est plus écrit ici mais dans
  -- offices_types.signe_planche : le Rite peut décider demain que le
  -- Grand Expert signe aussi, sans qu'on touche à ce fichier.
);

CREATE UNIQUE INDEX idx_signatures_office ON planche_signatures(planche_id, office);
