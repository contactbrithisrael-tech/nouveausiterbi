CREATE TABLE loges (
  id INTEGER PRIMARY KEY,
  nom TEXT NOT NULL,
  numero TEXT,
  orient TEXT,
  cree_le TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE utilisateurs (
  id INTEGER PRIMARY KEY,
  loge_id INTEGER NOT NULL REFERENCES loges(id),
  courriel TEXT NOT NULL UNIQUE,
  nom TEXT,
  charge TEXT NOT NULL CHECK (charge IN ('secretariat','tresorerie','venerable')),
  mdp_hash TEXT NOT NULL,
  mdp_sel TEXT NOT NULL,
  actif INTEGER NOT NULL DEFAULT 1,
  cree_le TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE sessions (
  jeton_hash TEXT PRIMARY KEY,
  utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
  cree_le TEXT NOT NULL DEFAULT (datetime('now')),
  expire_le TEXT NOT NULL
);

CREATE TABLE etat (
  loge_id INTEGER PRIMARY KEY REFERENCES loges(id),
  donnees TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  modifie_le TEXT NOT NULL DEFAULT (datetime('now')),
  modifie_par INTEGER REFERENCES utilisateurs(id)
);

CREATE TABLE journal (
  id INTEGER PRIMARY KEY,
  loge_id INTEGER,
  utilisateur_id INTEGER,
  quoi TEXT NOT NULL,
  le TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_sessions_expire ON sessions(expire_le);
CREATE INDEX idx_journal_loge ON journal(loge_id, le);

INSERT INTO loges (id, nom, numero, orient)
VALUES (1, 'Bereshit', '00', 'Alliance');
