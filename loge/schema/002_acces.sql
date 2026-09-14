-- ═══════════════════════════════════════════════════════════════════
--  RITE BRITH ISRAËL — Gestion des Loges
--  Migration 002 : ACCÈS, SESSIONS ET TRAÇABILITÉ
--
--  Ce fichier remplace l'authentification actuelle de
--  espace-membres.html, qui se déverrouille en JavaScript dans le
--  navigateur : n'importe qui lisant le code source de la page y
--  accède. C'est sans conséquence pour du contenu de présentation ;
--  c'est disqualifiant dès qu'on y met un tableau de loge.
--
--  Quatre décisions de sécurité sont inscrites dans ce schéma, et
--  chacune répond à la même question : « que se passe-t-il le jour où
--  cette base est copiée ? »
--
--  1. Le mot de passe n'est jamais stocké, seulement son empreinte.
--  2. Le jeton de session n'est jamais stocké non plus, seulement son
--     empreinte : une copie de la base ne permet pas de se faire
--     passer pour un Officier connecté.
--  3. Le secret 2FA est chiffré avec une clé qui n'est PAS dans la
--     base — elle vit dans les secrets Cloudflare. Sans cela, une
--     copie de la base annule la double authentification.
--  4. L'adresse IP est tronquée. Savoir qu'une connexion vient d'un
--     réseau suffit ; savoir de quelle ligne exactement ne sert à rien
--     et constitue une donnée personnelle de plus à protéger.
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── Les comptes ────────────────────────────────────────────────────
-- Un compte est TOUJOURS rattaché à une personne du tableau : il n'y a
-- pas de compte anonyme, pas de compte de service, pas de compte
-- « secretariat » partagé. Une action doit toujours être imputable à
-- quelqu'un.
--
-- Les droits ne sont PAS ici. Ils se déduisent de la table « offices »
-- (migration 001) : le Trésorier en exercice voit la comptabilité, son
-- prédécesseur ne la voit plus le lendemain de la passation, sans que
-- personne ait à penser à lui retirer quoi que ce soit. La seule
-- exception est le rôle global ci-dessous.
CREATE TABLE utilisateurs (
  id              INTEGER PRIMARY KEY,
  membre_id       INTEGER NOT NULL UNIQUE
                  REFERENCES membres(id) ON DELETE CASCADE,

  -- Authentification. PBKDF2-HMAC-SHA256 : c'est l'algorithme le plus
  -- solide disponible nativement dans WebCrypto sur Cloudflare Workers.
  -- Argon2id serait préférable mais impose un module WASM ; le nombre
  -- d'itérations est stocké par ligne pour pouvoir être relevé plus
  -- tard sans invalider les mots de passe existants.
  mdp_empreinte   TEXT    NOT NULL,
  mdp_sel         TEXT    NOT NULL,
  mdp_iterations  INTEGER NOT NULL DEFAULT 600000,
  mdp_change_le   TEXT,
  doit_changer_mdp INTEGER NOT NULL DEFAULT 1,  -- vrai à la création

  -- Double authentification (TOTP). Obligatoire pour les Officiers qui
  -- accèdent au tableau complet ; le secret est chiffré, jamais en clair.
  totp_secret_chiffre TEXT,
  totp_actif      INTEGER NOT NULL DEFAULT 0,

  -- Rôle global, indépendant de tout office. Sert uniquement à
  -- l'administration de l'outil lui-même (créer un atelier, ouvrir un
  -- exercice, restaurer une sauvegarde). Doit rester exceptionnel :
  -- deux personnes au plus.
  role_global     TEXT    NOT NULL DEFAULT 'aucun',

  actif           INTEGER NOT NULL DEFAULT 1,
  derniere_connexion TEXT,
  echecs_consecutifs INTEGER NOT NULL DEFAULT 0,
  bloque_jusqu_a  TEXT,                     -- temporisation anti-force brute
  cree_le         TEXT    NOT NULL DEFAULT (datetime('now')),
  CHECK (role_global IN ('aucun','admin_obedience')),
  CHECK (actif IN (0,1) AND totp_actif IN (0,1) AND doit_changer_mdp IN (0,1))
);

CREATE INDEX idx_utilisateurs_membre ON utilisateurs(membre_id);

-- ── Les sessions ───────────────────────────────────────────────────
-- Une session ouverte est une ligne ici. Conséquence utile : un
-- Officier qui perd son téléphone peut voir ses sessions actives et
-- les fermer toutes, et le Vénérable peut fermer celles d'un membre
-- radié dans la seconde.
--
-- « jeton_empreinte » est le SHA-256 du jeton envoyé au navigateur.
-- Le jeton lui-même n'existe qu'en deux endroits : le cookie du
-- porteur, et sa mémoire vive le temps de la requête. Jamais en base,
-- jamais dans un journal.
CREATE TABLE sessions (
  id              INTEGER PRIMARY KEY,
  jeton_empreinte TEXT    NOT NULL UNIQUE,
  utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
  cree_le         TEXT    NOT NULL DEFAULT (datetime('now')),
  expire_le       TEXT    NOT NULL,
  vue_le          TEXT,                     -- dernière activité
  ip_tronquee     TEXT,                     -- 192.168.1.0, jamais l'adresse
  navigateur      TEXT,                     -- « Firefox / Windows », abrégé
  revoquee_le     TEXT,
  motif_revocation TEXT
);

CREATE INDEX idx_sessions_utilisateur ON sessions(utilisateur_id, revoquee_le);
CREATE INDEX idx_sessions_expiration ON sessions(expire_le);

-- ── Les jetons à usage unique ──────────────────────────────────────
-- Première connexion, mot de passe oublié, confirmation d'adresse.
-- Même principe : seule l'empreinte est stockée. Un jeton consommé
-- n'est pas supprimé mais daté, pour qu'une tentative de réutilisation
-- laisse une trace au lieu de ressembler à un jeton inconnu.
CREATE TABLE jetons (
  id              INTEGER PRIMARY KEY,
  jeton_empreinte TEXT    NOT NULL UNIQUE,
  utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
  usage           TEXT    NOT NULL,
  cree_le         TEXT    NOT NULL DEFAULT (datetime('now')),
  expire_le       TEXT    NOT NULL,
  consomme_le     TEXT,
  CHECK (usage IN ('premiere_connexion','mot_de_passe_oublie','confirmation_email'))
);

CREATE INDEX idx_jetons_expiration ON jetons(expire_le);

-- ── Le journal d'accès ─────────────────────────────────────────────
-- Obligation RGPD, mais surtout garantie interne : un tableau de loge
-- consultable sans trace est un tableau que personne ne peut défendre
-- le jour où il circule à l'extérieur. Le journal répond à « qui a
-- consulté ou exporté le fichier, et quand ».
--
-- On journalise les CONSULTATIONS de données sensibles et toutes les
-- écritures — pas chaque affichage de page, sinon le journal devient
-- illisible et donc inutile.
--
-- Purge automatique à 12 mois (tâche planifiée) : conserver un journal
-- indéfiniment recrée le problème qu'il devait résoudre.
CREATE TABLE journal_acces (
  id              INTEGER PRIMARY KEY,
  horodatage      TEXT    NOT NULL DEFAULT (datetime('now')),
  utilisateur_id  INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
  membre_id       INTEGER,                  -- copie conservée si le compte
                                            -- disparaît : la trace survit
  action          TEXT    NOT NULL,
  objet_table     TEXT,                     -- « membres », « ecritures »…
  objet_id        INTEGER,
  loge_id         INTEGER REFERENCES loges(id),
  detail          TEXT,                     -- JSON court, jamais de mot de passe
  ip_tronquee     TEXT,
  CHECK (action IN (
    'connexion','connexion_echouee','deconnexion',
    'consultation_tableau','consultation_fiche','export',
    'creation','modification','suppression',
    'envoi_convocation','acces_refuse','sauvegarde'
  ))
);

CREATE INDEX idx_journal_horodatage ON journal_acces(horodatage);
CREATE INDEX idx_journal_utilisateur ON journal_acces(utilisateur_id, horodatage);
CREATE INDEX idx_journal_action ON journal_acces(action, horodatage);
