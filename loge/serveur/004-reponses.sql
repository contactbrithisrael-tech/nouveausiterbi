/* ═══════════════════════════════════════════════════════════════════
   LES RÉPONSES À LA CONVOCATION

   L'écran de la Tenue portait cet aveu : « Dans la vraie application,
   ces réponses arrivent seules ; ici, cliquez à leur place. » La Sœur
   Secrétaire relevait donc sa boîte, lisait quatre-vingts courriels et
   cochait à la main — et le traiteur attendait un chiffre qu'elle
   recomptait la veille.

   Chaque convocation porte désormais un lien propre à son
   destinataire. Un clic, et la réponse est ici.

   ► LE JETON EST LA LIGNE. Trente-deux octets tirés au hasard : il
     n'est ni devinable, ni calculable à partir d'un autre. Qui l'a
     répond pour cette personne-là et pour cette tenue-là, et pour
     rien d'autre.

   ► UNE LIGNE PAR PERSONNE ET PAR TENUE. Répondre deux fois change la
     réponse, n'en ajoute pas une seconde. On garde la dernière : on
     change d'avis, c'est le propre d'une réponse.

   ► « versee » dit que la Secrétaire l'a reprise à son registre. La
     réponse reste ici : ce qu'une personne a répondu elle-même est
     une trace, et une trace ne s'efface pas parce qu'on l'a recopiée.
═══════════════════════════════════════════════════════════════════ */

CREATE TABLE reponses (
  jeton      TEXT PRIMARY KEY,
  loge_id    INTEGER NOT NULL REFERENCES loges(id),
  tenue      TEXT    NOT NULL,          -- la date de la tenue
  qui_type   TEXT    NOT NULL,          -- membre | visiteur | ami
  qui_id     INTEGER NOT NULL,
  nom        TEXT,                      -- pour l'afficher sans relire le registre
  courriel   TEXT,
  reponse    TEXT,                      -- present | excuse  (nul = pas encore)
  agapes     INTEGER,                   -- 1 oui, 0 non, nul = pas encore
  repondu_le TEXT,
  versee     INTEGER NOT NULL DEFAULT 0,
  cree_le    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX idx_reponses_qui
  ON reponses(loge_id, tenue, qui_type, qui_id);
CREATE INDEX idx_reponses_attente
  ON reponses(loge_id, tenue, versee);
