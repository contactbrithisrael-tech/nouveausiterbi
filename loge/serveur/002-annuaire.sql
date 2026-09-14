/* ═══════════════════════════════════════════════════════════════════
   LES FICHES REÇUES DE L'ANNUAIRE

   Le formulaire de l'Espace Membres part aujourd'hui vers une boîte
   aux lettres. Quelqu'un ouvre le courriel, sélectionne, copie, et
   colle dans le programme. Ce qui n'est pas fait ce soir-là n'est
   jamais fait.

   Les fiches arrivent désormais ici, et le programme les verse au
   carnet des Visiteurs tout seul.

   ► ELLES NE VONT PAS DIRECTEMENT DANS LE REGISTRE. Cette table est
     une boîte aux lettres, pas le registre de l'Atelier. Le registre
     (table « etat ») ne s'écrit qu'avec une session ouverte ; ici, on
     dépose. La différence compte le jour où quelqu'un déposera autre
     chose que ce qu'on attendait.

   ► « versee » dit que la fiche a rejoint le carnet. Elle n'est pas
     effacée pour autant : une fiche reçue est une trace, et une trace
     ne s'efface pas parce qu'on l'a recopiée.
═══════════════════════════════════════════════════════════════════ */

CREATE TABLE annuaire (
  id       INTEGER PRIMARY KEY,
  loge_id  INTEGER NOT NULL REFERENCES loges(id),
  recu_le  TEXT    NOT NULL DEFAULT (datetime('now')),
  source   TEXT,                        -- d'où vient la fiche
  donnees  TEXT    NOT NULL,            -- la fiche telle qu'elle est arrivée
  versee   INTEGER NOT NULL DEFAULT 0,  -- a rejoint le carnet des Visiteurs
  versee_le TEXT
);

CREATE INDEX idx_annuaire_attente ON annuaire(loge_id, versee, id);
