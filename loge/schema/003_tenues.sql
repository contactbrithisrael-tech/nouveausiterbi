-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 003 : TENUES, TRAVAUX ET PRÉSENCES
--
--  Ce fichier est écrit d'après les documents réels de la R∴L∴
--  BERESHIT n°00 : la matrice de convocation, l'en-tête et la planche
--  à tracer. Chaque colonne correspond à quelque chose qui figure
--  effectivement sur l'un de ces documents. Rien n'y a été ajouté
--  « au cas où ».
--
--  Deux enseignements de ces documents sont inscrits dans le schéma :
--
--  1. L'ORIENT N'EST PAS L'ADRESSE. Bereshit est à l'Orient de
--     l'Alliance et tient ses travaux au Temple Le Venaqui, à
--     Ventabren. Confondre les deux, c'est ce qui a produit la
--     planche à tracer qui situe la loge à Salon-de-Provence.
--
--  2. LÀ OÙ IL Y A UNE VARIABLE, IL NE DOIT PLUS Y AVOIR DE TEXTE
--     LIBRE. Le modèle de planche fourni porte encore le nom d'une
--     loge d'un autre rite et d'une autre obédience, parce qu'il a été
--     recopié à la main. Toute donnée que la base connaît est calculée,
--     jamais retapée.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── Nomenclature des degrés ────────────────────────────────────────
-- Les degrés du RBI portent des noms propres au Rite : le premier est
-- « Apprenti-Boneh ». Je ne connais pas les trente-deux autres et je
-- ne les invente pas : cette table est à remplir par le Rite, et le
-- logiciel lit les noms ici plutôt que de les coder en dur.
--
-- « rite » permet aussi de décrire le REAA, pour les qualifications
-- acquises ailleurs (voir table suivante).
CREATE TABLE nomenclature_degres (
  id            INTEGER PRIMARY KEY,
  rite          TEXT    NOT NULL DEFAULT 'RBI',
  degre         INTEGER NOT NULL,
  nom           TEXT    NOT NULL,          -- « Apprenti-Boneh »
  nom_feminin   TEXT,                      -- atelier mixte : « Apprentie-Boneh »
  abreviation   TEXT,                      -- « App∴ B∴ »
  nom_hebreu    TEXT,
  CHECK (degre BETWEEN 1 AND 33)
);

CREATE UNIQUE INDEX idx_nomenclature ON nomenclature_degres(rite, degre);

-- Les trois degrés symboliques, définis par la Constitution V9
-- (Article des grades) : « Oved (עובד) — le Serviteur, nom du 1er
-- degré », « Boneh (בונה) — le Bâtisseur, nom du 2ème degré »,
-- « Adon (אדון) — le Maître, nom du 3ème degré ». Les degrés 4 à 33
-- restent à nommer.
--
-- ► La matrice de convocation du 7 septembre 2026 imprime « au Premier
--   Degré — Apprenti-Boneh ». Boneh nomme le DEUXIÈME degré : cette
--   convocation annonce une initiation au premier degré sous le nom du
--   second. C'est elle qui est fautive, pas cette table — et c'est le
--   genre d'erreur que cette table existe pour rendre impossible.
INSERT INTO nomenclature_degres (rite, degre, nom, nom_feminin, abreviation, nom_hebreu) VALUES
  ('RBI', 1, 'Apprenti Oved',   'Apprentie Oved',   'App∴ O∴',  'עובד'),
  ('RBI', 2, 'Compagnon Boneh', 'Compagnonne Boneh','Comp∴ B∴', 'בונה'),
  ('RBI', 3, 'Maître Adon',     'Maîtresse Adon',   'M∴ A∴',    'אדון');

-- ── Qualifications acquises hors du Rite ───────────────────────────
-- La planche à tracer désigne les membres par leur grade d'origine :
-- « MM∴ de rite Écossais Ancien & Accepté », « App M∴ ». Ces grades
-- ne sont pas des degrés RBI et ne doivent pas être mélangés à eux
-- dans la table « degres » : un Maître Maçon du REAA affilié au RBI
-- n'est pas pour autant 3e degré du RBI.
CREATE TABLE qualifications_externes (
  id            INTEGER PRIMARY KEY,
  membre_id     INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  rite          TEXT    NOT NULL,          -- « REAA », « RF », « RER »…
  degre         INTEGER,
  intitule      TEXT    NOT NULL,          -- tel qu'il doit être imprimé
  obedience     TEXT,                      -- « GLNRM », « GLDF »…
  date_obtention TEXT,
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_qualifications_membre ON qualifications_externes(membre_id);

-- ── Les tenues ─────────────────────────────────────────────────────
-- Colonnes relevées une à une sur la matrice de convocation de
-- Bereshit. Deux horaires, parce que le document en porte deux :
-- 17h30 pour la répétition, 19h30 pour l'ouverture des travaux.
--
-- Aucune donnée calculable n'est stockée. L'année de Vraie Lumière ne
-- figure pas ici : elle vaut l'année vulgaire + 4000 (« 6025 A∴V∴L∴ »
-- pour 2025, d'après la planche à tracer fournie) et se calcule à
-- l'impression. Une donnée recopiée est une donnée qui finit fausse.
CREATE TABLE tenues (
  id              INTEGER PRIMARY KEY,
  loge_id         INTEGER NOT NULL REFERENCES loges(id),
  date            TEXT    NOT NULL,
  heure_convocation TEXT,                  -- « 17:30 » — répétition, office
  heure_ouverture TEXT    NOT NULL,        -- « 19:30 » — ouverture des travaux
  type            TEXT    NOT NULL,
  titre           TEXT,                    -- « TENUE D'OBLIGATION », imprimé tel quel
  degre           INTEGER NOT NULL DEFAULT 1,

  -- Le lieu physique. Distinct de l'orient, qui appartient à la loge.
  lieu_nom        TEXT,                    -- « Temple Le Venaqui »
  lieu_adresse    TEXT,                    -- « Ancienne Route d'Éguilles »
  lieu_code_postal TEXT,
  lieu_ville      TEXT,

  adage           TEXT,                    -- « L'assiduité aux travaux est le
                                           --   premier devoir du Maçon »
  statut          TEXT    NOT NULL DEFAULT 'prevue',
  cree_le         TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (degre BETWEEN 1 AND 33),
  CHECK (type IN (
    'obligation','initiation','passage','elevation','installation',
    'blanche_fermee','blanche_ouverte','assemblee_generale',
    'saint_jean','funebre','convent','conference'
  )),
  CHECK (statut IN ('prevue','tenue','annulee','reportee'))
);

CREATE INDEX idx_tenues_loge_date ON tenues(loge_id, date);
CREATE INDEX idx_tenues_date ON tenues(date);

-- ── Les agapes ─────────────────────────────────────────────────────
-- Séparées des tenues : toute tenue n'a pas d'agapes, et une agape a
-- sa propre date limite d'inscription, son propre prix et son propre
-- traiteur. La convocation de septembre porte « inscription avant le
-- 3 septembre, le triangle sera de 25 € environ » — le prix est donc
-- indicatif au moment de la convocation, et arrêté ensuite.
CREATE TABLE agapes (
  id              INTEGER PRIMARY KEY,
  tenue_id        INTEGER NOT NULL UNIQUE REFERENCES tenues(id) ON DELETE CASCADE,
  lieu            TEXT,
  traiteur        TEXT,
  prix_indicatif  REAL,                    -- annoncé sur la convocation
  prix_definitif  REAL,                    -- arrêté après le devis
  date_limite_inscription TEXT,
  commentaire     TEXT,
  cree_le         TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── L'ordre du jour ────────────────────────────────────────────────
-- Une ligne par point, dans l'ordre. « travail_id » relie le point au
-- travail programmé à l'année, quand il s'agit d'une planche : le
-- programme annuel et la convocation cessent alors d'être deux
-- documents à tenir à jour séparément.
CREATE TABLE ordre_du_jour (
  id              INTEGER PRIMARY KEY,
  tenue_id        INTEGER NOT NULL REFERENCES tenues(id) ON DELETE CASCADE,
  rang            INTEGER NOT NULL,
  heure           TEXT,                    -- facultatif : « 17:30 »
  libelle         TEXT    NOT NULL,
  travail_id      INTEGER REFERENCES travaux(id) ON DELETE SET NULL,
                                           -- SQLite résout les clés
                                           -- étrangères à l'insertion, pas
                                           -- à la création : la table visée
                                           -- est déclarée plus bas et la
                                           -- contrainte s'applique quand même.
  duree_minutes   INTEGER                  -- « 5' de symbolisme »
);

CREATE UNIQUE INDEX idx_odj_rang ON ordre_du_jour(tenue_id, rang);

-- ── Les travaux : le programme des planches à l'année ──────────────
-- « Planche » désigne deux choses différentes, et les confondre rend
-- le programme annuel inexploitable :
--   • le TRAVAIL présenté en tenue par un Frère ou une Sœur — c'est
--     ce qui se planifie à l'année, et c'est cette table ;
--   • la PLANCHE À TRACER, compte rendu de la tenue rédigé par le
--     Secrétaire — migration 004.
--
-- Un travail existe dès qu'il est proposé, avant même d'être rattaché
-- à une tenue : c'est ce qui permet au Vénérable de bâtir le
-- programme de la saison à partir d'une réserve de sujets.
CREATE TABLE travaux (
  id              INTEGER PRIMARY KEY,
  loge_id         INTEGER NOT NULL REFERENCES loges(id),
  saison          TEXT    NOT NULL,        -- « 2026-2027 », en années vulgaires
  sujet           TEXT    NOT NULL,
  auteur_membre_id INTEGER REFERENCES membres(id) ON DELETE SET NULL,
  auteur_externe  TEXT,                    -- conférencier invité, non membre
  type            TEXT    NOT NULL DEFAULT 'planche',
  degre           INTEGER NOT NULL DEFAULT 1,
  duree_minutes   INTEGER,
  tenue_id        INTEGER REFERENCES tenues(id) ON DELETE SET NULL,
  statut          TEXT    NOT NULL DEFAULT 'propose',
  fichier_cle     TEXT,                    -- texte du travail déposé dans R2
  cree_le         TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (degre BETWEEN 1 AND 33),
  CHECK (type IN ('planche','symbolisme','accueil','cantonade',
                  'architecture','conference','rapport')),
  CHECK (statut IN ('propose','valide','programme','presente','reporte','annule')),
  CHECK (auteur_membre_id IS NOT NULL OR auteur_externe IS NOT NULL)
);

CREATE INDEX idx_travaux_saison ON travaux(loge_id, saison);
CREATE INDEX idx_travaux_tenue ON travaux(tenue_id);
CREATE INDEX idx_travaux_auteur ON travaux(auteur_membre_id);

-- ── Les visiteurs ──────────────────────────────────────────────────
-- ATTENTION : un visiteur n'est PAS membre du Rite. L'exception RGPD
-- qui vous autorise à tenir le tableau de vos membres (article 9.2.d,
-- organismes à finalité philosophique, « se rapportant exclusivement
-- aux membres ») ne le couvre pas. Sa fiche exige donc un consentement
-- explicite et une conservation courte — d'où « consentement_le » et
-- la purge automatique appuyée sur « derniere_visite ».
--
-- Le minimum utile, et rien de plus : de quoi le tuiler et le
-- reconvoquer s'il le souhaite.
CREATE TABLE visiteurs (
  id              INTEGER PRIMARY KEY,
  nom             TEXT    NOT NULL,
  prenoms         TEXT,
  loge_origine    TEXT,
  orient_origine  TEXT,
  obedience       TEXT,
  rite            TEXT,
  degre_declare   TEXT,                    -- tel qu'il se déclare : « MM∴ REAA »
  email           TEXT,
  telephone       TEXT,
  consentement_le TEXT,                    -- NULL = ne pas recontacter
  derniere_visite TEXT,
  cree_le         TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_visiteurs_nom ON visiteurs(nom, prenoms);
CREATE INDEX idx_visiteurs_purge ON visiteurs(derniere_visite);

-- ── Les présences ──────────────────────────────────────────────────
-- Le fait, pas l'intention. « source » distingue ce qu'un membre a
-- annoncé de ce qui a été constaté sur la feuille signée : c'est la
-- feuille signée qui fait foi pour le quorum d'une assemblée, jamais
-- une case cochée dans une base.
CREATE TABLE presences (
  id              INTEGER PRIMARY KEY,
  tenue_id        INTEGER NOT NULL REFERENCES tenues(id) ON DELETE CASCADE,
  membre_id       INTEGER REFERENCES membres(id) ON DELETE CASCADE,
  visiteur_id     INTEGER REFERENCES visiteurs(id) ON DELETE CASCADE,
  statut          TEXT    NOT NULL,
  source          TEXT    NOT NULL DEFAULT 'declaratif',
  tuile_par       INTEGER REFERENCES membres(id) ON DELETE SET NULL,
  aux_agapes      INTEGER NOT NULL DEFAULT 0,
  regime          TEXT,                    -- casher, végétarien, allergie…
  saisi_par       INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  saisi_le        TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (statut IN ('present','excuse','absent','attendu')),
  CHECK (source IN ('declaratif','reponse_convocation','emargement_signe')),
  CHECK (aux_agapes IN (0,1)),
  -- Un membre OU un visiteur, jamais les deux, jamais aucun.
  CHECK ((membre_id IS NOT NULL) <> (visiteur_id IS NOT NULL))
);

CREATE UNIQUE INDEX idx_presences_membre ON presences(tenue_id, membre_id)
  WHERE membre_id IS NOT NULL;
CREATE UNIQUE INDEX idx_presences_visiteur ON presences(tenue_id, visiteur_id)
  WHERE visiteur_id IS NOT NULL;
