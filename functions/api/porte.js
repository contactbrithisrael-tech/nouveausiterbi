/* ═══════════════════════════════════════════════════════════════════
   L'ÉTAT DE LA PORTE

   Une seule question, et la réponse ne coûte rien à personne :
   « ce serveur est-il en état de reconnaître quelqu'un ? »

   ► POURQUOI. La page porte encore, en clair, l'empreinte de deux
     mots de passe — ceux du premier jour. C'est ce qui a sauvé la Sœur
     Secrétaire le soir où la table des utilisateurs était vide : le
     serveur refusait tout le monde, et elle est entrée quand même.

     Mais cette même empreinte rendrait tout changement de mot de passe
     illusoire : qui taperait l'ancien serait refusé par le serveur,
     puis accepté par la page. Personne ne pourrait plus être révoqué,
     et personnaliser son mot de passe ne servirait à rien.

     D'où cette question. AUCUN COMPTE : le serveur ne peut reconnaître
     personne, son refus n'apprend rien, et la page reprend la main —
     en le disant. AU MOINS UN COMPTE : le serveur sait faire son
     office, son refus est un vrai refus, et la page se tait.

   ► CE QUI SORT D'ICI. Un booléen et un nombre. Pas un nom, pas une
     adresse, pas une empreinte. Savoir que l'Atelier a deux Officiers
     enregistrés n'apprend rien qu'on ne lise sur son tableau.
═══════════════════════════════════════════════════════════════════ */

import { json } from './_commun.js';

export async function onRequestGet(context){
  try {
    const r = await context.env.DB.prepare(
      'SELECT COUNT(*) AS n FROM utilisateurs WHERE actif = 1').first();
    return json({ serveur: true, comptes: Number(r?.n ?? 0) });
  } catch (e) {
    /* La base est absente ou hors d'usage : le serveur répond, mais il
       ne peut reconnaître personne. C'est exactement le cas « aucun
       compte », et il doit être traité comme tel — sans quoi une
       liaison manquante refermerait la porte sur tout le monde. */
    return json({ serveur: true, comptes: 0, base: false });
  }
}
