-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 004 : ENVOIS, INVITATIONS ET RÉPONSES
--
--  Cette migration a une seule raison d'être : que la Secrétaire ne
--  saisisse plus jamais une réponse. Elle clique « envoyer », chaque
--  destinataire reçoit SON lien, et les réponses tombent dans le
--  tableau toutes seules.
--
--  Trois règles y sont inscrites, et aucune n'est négociable :
--
--  1. UN ENVOI PAR DESTINATAIRE. Il n'existe pas de colonne « copie »
--     ni « copie cachée » dans ce schéma. Trente adresses dans un même
--     message, c'est le tableau de la loge publié — et une copie
--     cachée reste un accident de clic.
--
--  2. UN LIEN PAR PERSONNE, JAMAIS UN LIEN PUBLIC. Un lien
--     d'inscription qu'on demande aux membres de recopier et de faire
--     circuler est, par construction, ouvert à quiconque le reçoit :
--     il annonce à un inconnu le nom de la loge, la date et le lieu de
--     ses travaux. Ici, chaque jeton ne vaut que pour une personne et
--     une tenue.
--
--  3. UN ENVOI SE PRÉPARE, PUIS SE DÉCLENCHE. Rien ne part sans un
--     geste humain. Une convocation expédiée par un automate mal
--     réglé ne se rattrape pas.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── Les invitations ────────────────────────────────────────────────
-- Un Frère invite quelqu'un à une tenue. L'invité n'a pas de compte,
-- ne se connecte pas, et n'a rien à installer : il reçoit un lien qui
-- ne vaut que pour lui et répond en deux clics.
--
-- L'invité est saisi ici, pas dans « visiteurs » : tant qu'il n'est
-- pas venu, ce n'est pas un visiteur, c'est une intention. Sa fiche de
-- visiteur n'est créée que le jour où il se présente — ce qui évite de
-- constituer un fichier de personnes qui ne sont jamais venues.
CREATE TABLE invitations (
  id            INTEGER PRIMARY KEY,
  tenue_id      INTEGER NOT NULL REFERENCES tenues(id) ON DELETE CASCADE,
  invite_par    INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
  visiteur_id   INTEGER REFERENCES visiteurs(id) ON DELETE SET NULL,
  nom           TEXT    NOT NULL,
  prenoms       TEXT,
  email         TEXT    NOT NULL,
  loge_origine  TEXT,
  obedience     TEXT,
  degre_declare TEXT,
  jeton_empreinte TEXT  NOT NULL UNIQUE,   -- empreinte du lien personnel
  statut        TEXT    NOT NULL DEFAULT 'preparee',
  aux_agapes    INTEGER,                   -- NULL tant qu'il n'a pas répondu
  regime        TEXT,
  repondu_le    TEXT,
  expire_le     TEXT    NOT NULL,          -- le lien meurt après la tenue
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (statut IN ('preparee','envoyee','ouverte','confirmee','declinee','expiree')),
  CHECK (aux_agapes IS NULL OR aux_agapes IN (0,1))
);

CREATE INDEX idx_invitations_tenue ON invitations(tenue_id, statut);
CREATE INDEX idx_invitations_parrain ON invitations(invite_par);

-- ── Les campagnes ──────────────────────────────────────────────────
-- Un geste de la Secrétaire = une campagne. Elle prépare, relit, puis
-- déclenche. Tant que « declenche_le » est vide, rien n'est parti et
-- tout est modifiable.
--
-- Le même objet sert à la convocation, au rappel de capitation et à
-- la relance d'agapes : ce sont trois textes différents, pas trois
-- mécaniques différentes. Un seul écran à apprendre.
CREATE TABLE campagnes (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  type          TEXT    NOT NULL,
  tenue_id      INTEGER REFERENCES tenues(id) ON DELETE CASCADE,
  objet         TEXT    NOT NULL,          -- objet du courriel
  corps         TEXT,                      -- texte libre ajouté au gabarit
  statut        TEXT    NOT NULL DEFAULT 'brouillon',
  prepare_par   INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  declenche_par INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  declenche_le  TEXT,                      -- vide = rien n'est parti
  cree_le       TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (type IN (
    'convocation','rappel_convocation','rappel_agapes',
    'appel_capitation','relance_capitation',
    'planche_a_approuver','agenda_loges_amies','information'
  )),
  CHECK (statut IN ('brouillon','prete','en_cours','terminee','annulee')),
  -- Une campagne déclenchée l'a été par quelqu'un, et réciproquement.
  CHECK ((declenche_le IS NULL) = (declenche_par IS NULL))
);

CREATE INDEX idx_campagnes_loge ON campagnes(loge_id, cree_le);
CREATE INDEX idx_campagnes_tenue ON campagnes(tenue_id);

-- ── Les envois ─────────────────────────────────────────────────────
-- UNE LIGNE PAR DESTINATAIRE. C'est la table qui garantit qu'aucun
-- message ne part à plusieurs personnes à la fois : il n'y a pas
-- d'autre chemin d'envoi dans le logiciel.
--
-- Elle répond aussi à la question que la Secrétaire se pose vraiment,
-- « qui n'a pas reçu, qui n'a pas ouvert, qui n'a pas répondu », sans
-- qu'elle ait à tenir une liste à côté.
--
-- « jeton_empreinte » porte le lien de réponse personnel. Comme
-- partout ailleurs dans ce schéma, seule l'empreinte est stockée : le
-- lien n'existe que dans le courriel de son destinataire.
CREATE TABLE envois (
  id            INTEGER PRIMARY KEY,
  campagne_id   INTEGER NOT NULL REFERENCES campagnes(id) ON DELETE CASCADE,
  membre_id     INTEGER REFERENCES membres(id) ON DELETE CASCADE,
  invitation_id INTEGER REFERENCES invitations(id) ON DELETE CASCADE,
  email         TEXT    NOT NULL,
  jeton_empreinte TEXT  UNIQUE,
  statut        TEXT    NOT NULL DEFAULT 'a_envoyer',
  envoye_le     TEXT,
  ouvert_le     TEXT,
  repondu_le    TEXT,
  erreur        TEXT,                      -- « adresse inexistante », etc.
  reference_fournisseur TEXT,              -- identifiant du message chez Brevo,
                                           -- pour retrouver un envoi contesté
  CHECK (statut IN ('a_envoyer','envoye','ouvert','repondu','erreur','annule')),
  -- Un membre OU un invité, jamais les deux, jamais aucun.
  CHECK ((membre_id IS NOT NULL) <> (invitation_id IS NOT NULL))
);

CREATE UNIQUE INDEX idx_envois_membre ON envois(campagne_id, membre_id)
  WHERE membre_id IS NOT NULL;
CREATE UNIQUE INDEX idx_envois_invitation ON envois(campagne_id, invitation_id)
  WHERE invitation_id IS NOT NULL;
CREATE INDEX idx_envois_statut ON envois(campagne_id, statut);
