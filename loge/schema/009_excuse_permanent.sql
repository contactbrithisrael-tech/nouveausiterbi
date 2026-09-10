-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 009 : L'EXCUSE PERMANENTE
--
--  Un membre peut être empêché durablement sans cesser d'être membre :
--  le TIF Philippe NAKACHE réside en Nouvelle-Calédonie, le TIF Laurent
--  NOTARIANNI est excusé pour une durée indéterminée.
--
--  Ce n'est AUCUN des statuts existants, et les confondre fausserait
--  le tableau :
--    • ce n'est pas « en sommeil » — un membre en sommeil ne travaille
--      plus, celui-ci reste des colonnes et doit être convoqué ;
--    • ce n'est pas « absent » — l'absence se constate au soir de la
--      tenue, l'excuse permanente est connue d'avance ;
--    • ce n'est pas « exempté de capitation » — Philippe NAKACHE paie
--      la sienne, Laurent NOTARIANNI en est exempté comme membre
--      d'honneur ad vitam. Les deux choses sont indépendantes, d'où
--      deux colonnes et non une.
--
--  Conséquence pratique, et c'est là tout l'intérêt : à l'ouverture
--  d'une tenue, ces membres figurent d'emblée parmi les excusés, sur
--  la feuille d'émargement comme sur la planche à tracer. Personne n'a
--  à les cocher, mois après mois, jusqu'à l'oubli.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

ALTER TABLE membres ADD COLUMN excuse_permanent INTEGER NOT NULL DEFAULT 0;
ALTER TABLE membres ADD COLUMN motif_excuse TEXT;
ALTER TABLE membres ADD COLUMN excuse_depuis TEXT;

CREATE INDEX idx_membres_excuse ON membres(excuse_permanent);

-- Qui convoquer, et dans quel état l'inscrire d'office. C'est cette vue
-- que lit la préparation d'une tenue : elle répond en une fois à « qui
-- reçoit la convocation » et « qui est excusé sans avoir à le dire ».
CREATE VIEW convocables AS
SELECT m.id                AS membre_id,
       a.loge_id           AS loge_id,
       m.nom, m.prenoms, m.email,
       m.statut,
       CASE WHEN m.excuse_permanent = 1 THEN 'excuse' ELSE 'attendu' END AS presence_initiale,
       m.motif_excuse,
       CASE WHEN m.statut = 'honoraire' THEN 0 ELSE 1 END AS soumis_capitation
FROM membres m
JOIN affiliations a ON a.membre_id = m.id AND a.date_fin IS NULL
WHERE m.statut IN ('actif','honoraire');
