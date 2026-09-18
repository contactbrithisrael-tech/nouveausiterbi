/* ═══════════════════════════════════════════════════════════════════
   CE QUI PORTE LE COURRIER

   Le programme n'envoyait rien : il ouvrait la messagerie de la Sœur
   Secrétaire avec un lien « mailto: ». Cela marche pour dix
   destinataires et cesse de marcher pour quatre-vingts — le lien est
   coupé, en silence, et l'on croit avoir convoqué l'Atelier.

   Un service d'envoi change cela : le serveur remet les messages, et
   sait ce que le service en a dit.

   ► UN SEUL APPEL POUR TOUT LE MONDE. Cloudflare borne le nombre de
     requêtes qu'une fonction peut faire : quatre-vingts envois =
     quatre-vingts requêtes, et la fonction est arrêtée en chemin. Les
     deux services retenus savent prendre la liste entière d'un coup.
     C'est la raison de ce choix, et non l'élégance.

   ► UN MESSAGE PAR PERSONNE, jamais une liste en copie. Chacun reçoit
     le sien, adressé à lui. Personne ne lit l'adresse des autres, et
     l'on sait pour chacun ce que le service a répondu.

   ► AUCUNE CLÉ N'EST ÉCRITE ICI. Elle vit dans les variables
     d'environnement de Cloudflare, chiffrées, et ne sort jamais du
     serveur. Ce fichier est public ; la clé ne l'est pas.

   ► SANS CLÉ, ON NE FAIT PAS SEMBLANT. La fonction dit qu'elle n'est
     pas configurée, et le programme retombe sur l'ancien chemin —
     la messagerie ouverte à la main. Un envoi qui échoue en silence
     serait pire que pas d'envoi du tout.
═══════════════════════════════════════════════════════════════════ */

const LIMITE_LOT = 200;     // au-delà, on découpe

/* Quel service est configuré ? Le premier trouvé l'emporte. */
export function fournisseur(env){
  if (env && env.BREVO_CLE)  return { nom: 'brevo',  cle: env.BREVO_CLE };
  if (env && env.RESEND_CLE) return { nom: 'resend', cle: env.RESEND_CLE };
  return null;
}

export function expediteur(env){
  /* L'adresse qui apparaît comme expéditeur. Elle doit être vérifiée
     chez le service, sans quoi rien ne part. */
  return {
    adresse: (env && env.COURRIEL_EXPEDITEUR) || '',
    nom: (env && env.COURRIEL_NOM) || 'R∴L∴ Bereshit n°00'
  };
}

/* ── BREVO ──────────────────────────────────────────────────────────
   « messageVersions » porte jusqu'à deux mille destinataires en un
   seul appel, chacun recevant son propre message. */
async function envoyerBrevo(cle, de, sujet, corps, liste){
  const r = await fetch('https://api.brevo.com/v3/smtp/email', {
    method: 'POST',
    headers: { 'api-key': cle, 'content-type': 'application/json',
               'accept': 'application/json' },
    body: JSON.stringify({
      sender: { email: de.adresse, name: de.nom },
      subject: sujet,
      textContent: corps,
      messageVersions: liste.map(a => ({ to: [{ email: a }] }))
    })
  });
  const texte = await r.text();
  if (r.ok) return liste.map(a => ({ adresse: a, statut: 'partie', detail: '' }));
  return liste.map(a => ({ adresse: a, statut: 'refusee',
                           detail: ('HTTP ' + r.status + ' ' + texte).slice(0, 300) }));
}

/* ── RESEND ─────────────────────────────────────────────────────────
   L'envoi par lot accepte cent messages d'un coup, et répond pour
   chacun. */
async function envoyerResend(cle, de, sujet, corps, liste){
  const r = await fetch('https://api.resend.com/emails/batch', {
    method: 'POST',
    headers: { authorization: 'Bearer ' + cle, 'content-type': 'application/json' },
    body: JSON.stringify(liste.map(a => ({
      from: de.nom + ' <' + de.adresse + '>', to: [a],
      subject: sujet, text: corps
    })))
  });
  const texte = await r.text();
  if (!r.ok)
    return liste.map(a => ({ adresse: a, statut: 'refusee',
                             detail: ('HTTP ' + r.status + ' ' + texte).slice(0, 300) }));
  return liste.map(a => ({ adresse: a, statut: 'partie', detail: '' }));
}

/* ── L'ENTRÉE UNIQUE ────────────────────────────────────────────────
   Rend une ligne par destinataire. Ce qui a été refusé le dit, avec la
   raison telle que le service l'a donnée : inventer un message d'erreur
   ferait chercher la panne au mauvais endroit. */
export async function remettre(env, sujet, corps, destinataires){
  const f = fournisseur(env);
  if (!f) return { configure: false, resultats: [] };
  const de = expediteur(env);
  if (!de.adresse)
    return { configure: false, pourquoi: 'expediteur_manquant', resultats: [] };

  const resultats = [];
  for (let i = 0; i < destinataires.length; i += LIMITE_LOT){
    const lot = destinataires.slice(i, i + LIMITE_LOT);
    try {
      const r = f.nom === 'brevo'
        ? await envoyerBrevo(f.cle, de, sujet, corps, lot)
        : await envoyerResend(f.cle, de, sujet, corps, lot);
      resultats.push(...r);
    } catch (e) {
      resultats.push(...lot.map(a => ({ adresse: a, statut: 'refusee',
        detail: ('le service n’a pas répondu : ' + e).slice(0, 300) })));
    }
  }
  return { configure: true, service: f.nom, resultats };
}
