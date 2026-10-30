-- Convocations déposées par les Loges amies (onglet « Convocation de ma Loge visiteur »).
-- Chaque dépôt attend la décision du Secrétariat : validé, refusé, puis envoyé aux membres.
CREATE TABLE IF NOT EXISTS depots_convocation (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  loge_id     INTEGER NOT NULL,
  le          TEXT    NOT NULL DEFAULT (datetime('now')),
  loge_nom    TEXT    NOT NULL,
  nom_fichier TEXT    NOT NULL,
  type_mime   TEXT    NOT NULL,
  octets      INTEGER NOT NULL,
  contenu     TEXT    NOT NULL,           -- base64 ; une ligne D1 tient 2 Mo
  statut      TEXT    NOT NULL DEFAULT 'attente'
              CHECK (statut IN ('attente','validee','refusee','envoyee')),
  decide_par  INTEGER,
  decide_le   TEXT,
  envoye_le   TEXT,
  nb_envoyes  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_depots_statut ON depots_convocation (loge_id, statut, le);
