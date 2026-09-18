/* ═══════════════════════════════════════════════════════════════════
   LA TRACE DES ENVOIS

   Jusqu'ici le programme ouvrait la messagerie et ne savait plus rien :
   ni qui avait reçu, ni si quelque chose était parti. Une convocation
   qu'on croit envoyée et qui n'arrive pas, on ne l'apprend que le soir
   de la tenue, aux places vides.

   Chaque destinataire a désormais SA ligne, avec ce que le fournisseur
   a répondu pour lui. « Partie » ne veut pas dire « lue » — aucun envoi
   ne le garantit — mais cela veut dire que le service l'a acceptée,
   et c'est tout ce qu'un programme honnête peut affirmer.

   On garde l'adresse, pas le corps du message : le registre de
   l'Atelier porte déjà la convocation, et la recopier à
   quatre-vingts exemplaires n'apprendrait rien.
═══════════════════════════════════════════════════════════════════ */

CREATE TABLE IF NOT EXISTS envois (
  id            INTEGER PRIMARY KEY,
  loge_id       INTEGER NOT NULL REFERENCES loges(id),
  le            TEXT    NOT NULL DEFAULT (datetime('now')),
  par           INTEGER REFERENCES utilisateurs(id),
  sujet         TEXT    NOT NULL,
  groupe        TEXT,                 -- tous, membres, visiteurs, amis
  destinataire  TEXT    NOT NULL,
  statut        TEXT    NOT NULL,     -- partie | refusee
  detail        TEXT                  -- ce que le fournisseur a dit
);

CREATE INDEX IF NOT EXISTS idx_envois_loge ON envois(loge_id, le);
