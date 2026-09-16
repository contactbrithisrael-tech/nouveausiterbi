-- ═══════════════════════════════════════════════════════════════
--  MD Consulting — permanence conseil orientation / emploi
--  Modèle de données complet. Stockage 100 % local (SQLite).
--  ON DELETE CASCADE partout : effacer une Personne efface tout
--  ce qui la concerne (droit à l'effacement, art. 17 RGPD).
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS personne (
    id                        TEXT PRIMARY KEY,          -- UUID, clé utilisée partout
    nom                       TEXT NOT NULL,
    prenom                    TEXT NOT NULL,
    date_naissance            TEXT,                      -- ISO 8601 ; donne l'âge exact
    telephone                 TEXT,
    courriel                  TEXT,
    adresse                   TEXT,
    tranche_age               TEXT NOT NULL CHECK (tranche_age IN ('college','lycee','adulte')),
    public                    TEXT NOT NULL CHECK (public IN ('college','lycee','reconversion','vae','handicap')),
    situation                 TEXT,                      -- classe et établissement, ou situation professionnelle
    rqth                      INTEGER NOT NULL DEFAULT 0,
    representant_legal        TEXT,                      -- nom du parent ou tuteur
    representant_contact      TEXT,
    consentement_parental_date TEXT,                     -- ISO 8601 ; NULL = pas de consentement enregistré
    lien_mescompetences       TEXT,
    notes_libres              TEXT,
    date_creation             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seance (
    id                  TEXT PRIMARY KEY,
    personne_id         TEXT NOT NULL REFERENCES personne(id) ON DELETE CASCADE,
    date                TEXT NOT NULL,
    heure_debut         TEXT,
    chrono_max_minutes  INTEGER NOT NULL DEFAULT 90,
    objectif_texte      TEXT
);

CREATE TABLE IF NOT EXISTS resultat_test (
    id             TEXT PRIMARY KEY,
    seance_id      TEXT NOT NULL REFERENCES seance(id) ON DELETE CASCADE,
    type_test      TEXT NOT NULL CHECK (type_test IN (
                       'projet_de_vie','freins','motivations_35','valeurs','bilan_360',
                       'riasec_externe','big_five_externe','assessfirst_externe')),
    reponses_json  TEXT,
    synthese_texte TEXT,
    date_saisie    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rapport (
    id                 TEXT PRIMARY KEY,
    seance_id          TEXT NOT NULL REFERENCES seance(id) ON DELETE CASCADE,
    date_generation    TEXT NOT NULL,
    bloc_situation     TEXT,
    bloc_tests_utilises TEXT,
    bloc_resultats     TEXT,
    bloc_solutions     TEXT,
    export_docx_path   TEXT
);

CREATE INDEX IF NOT EXISTS idx_seance_personne  ON seance(personne_id);
CREATE INDEX IF NOT EXISTS idx_resultat_seance  ON resultat_test(seance_id);
CREATE INDEX IF NOT EXISTS idx_rapport_seance   ON rapport(seance_id);
