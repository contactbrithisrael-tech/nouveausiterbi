/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — blocage d'indexation des prévisualisations

   Cloudflare Pages publie une URL par déploiement, du type
   <identifiant>.<projet>.pages.dev. Ces adresses sont publiques et
   indexables : une ancienne version du site peut donc rester
   référencée par Google en parallèle du domaine officiel, avec les
   données qu'on croyait avoir retirées.

   Ce middleware ajoute l'en-tête X-Robots-Tag: noindex, nofollow à
   toute réponse servie depuis un hôte *.pages.dev.

   ► La condition porte sur ce qu'il faut bloquer, jamais sur ce qu'il
     faut autoriser. Une erreur ici ne peut donc pas désindexer
     www.brith-israel.org : le domaine officiel n'est jamais testé.
════════════════════════════════════════════════════════════════ */

export async function onRequest(context) {
  const response = await context.next();

  const host = (context.request.headers.get('host') || '').toLowerCase();
  const estPrevisualisation = host.endsWith('.pages.dev');

  if (!estPrevisualisation) return response;

  // La réponse d'origine est immuable : on la reconstruit pour pouvoir
  // écrire dans ses en-têtes.
  const copie = new Response(response.body, response);
  copie.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
  return copie;
}
