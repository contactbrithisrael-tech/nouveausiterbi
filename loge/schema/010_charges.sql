-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 010 : LES CHARGES TEMPORAIRES
--
--  Le TIF Jean-Marc SAFFARO est Maître des Banquets de Bereshit. Or la
--  Constitution dit que la Loge est dirigée par « trois Officiers, et
--  trois seulement ». J'avais conclu que la charge n'existait pas.
--
--  C'était lire à moitié. Le même article 9quater ajoute : « Les trois
--  Officiers peuvent désigner temporairement des Frères ou Sœurs pour
--  certaines tâches. » Le Maître des Banquets n'est donc pas un
--  quatrième Office — il est une CHARGE, confiée par le Collège des
--  Trois Lumières, et révocable par lui.
--
--  La distinction n'est pas formelle. Un Office s'élit et porte le
--  maillet ; une charge se confie et s'exerce. Les confondre ferait du
--  Maître des Banquets l'égal du Vénérable dans le tableau, et lui
--  donnerait la parole qu'il n'a pas.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- 'office' : élu, l'un des trois. 'charge' : désigné, temporaire.
ALTER TABLE offices_types ADD COLUMN nature TEXT NOT NULL DEFAULT 'office';

UPDATE offices_types SET nature = 'office'
 WHERE code IN ('venerable','premier_surveillant','second_surveillant');
UPDATE offices_types SET nature = 'dignite'
 WHERE rang >= 10;   -- les charges du Suprême Conseil, d'un autre ordre

-- Les charges qu'un Atelier confie. Cette liste s'allonge librement :
-- c'est le propre d'une désignation temporaire.
INSERT INTO offices_types (code, libelle, abreviation, rang, signe_planche, nature) VALUES
  ('maitre_banquets', 'Maître des Banquets', 'MDB∴', 4, 0, 'charge'),
  ('maitre_ceremonies','Maître des Cérémonies','MC∴',  5, 0, 'charge'),
  ('couvreur',        'Couvreur',            'Couv∴', 6, 0, 'charge'),
  ('archiviste',      'Archiviste',          'Arch∴', 7, 0, 'charge'),
  ('hospitalier',     'Hospitalier de l’Atelier','Hosp∴', 8, 0, 'charge');

-- Qui dirige, qui est chargé, qui est dignitaire — d'un coup d'œil.
CREATE VIEW charges_en_cours AS
SELECT o.loge_id, o.membre_id, m.nom, m.prenoms,
       t.libelle, t.abreviation, t.nature, t.rang, o.date_debut
FROM offices o
JOIN offices_types t ON t.code = o.office
JOIN membres m       ON m.id   = o.membre_id
WHERE o.date_fin IS NULL
ORDER BY o.loge_id, t.rang;
