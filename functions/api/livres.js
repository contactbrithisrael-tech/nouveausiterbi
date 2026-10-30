/* ═══════════════════════════════════════════════════════════════════
   DEMANDER UN LIVRE DU RITE, À SON DEGRÉ

   Un membre donne l'adresse de ses convocations. Le serveur le
   reconnaît au registre et lui montre TOUS les ouvrages de la liste.
   Sa demande part par courriel au Vénérable Maître Jean-Michel RAUX :
   c'est LUI qui décide si ce membre a droit à ce livre, puis règle
   l'impression et le paiement. Le courriel dit qui demande quoi, à
   quel degré il est inscrit au registre, et rien d'autre.

   ► LA LISTE VIENT DU CORPUS (joshua/corpus.json), par identifiants
     choisis ci-dessous. N'en sortent ni lien Drive ni source : un
     titre, un degré.
   ► LE DESTINATAIRE N'EST PAS DANS CE FICHIER : le dépôt est servi en
     clair. Il vit dans le secret Cloudflare LIVRES_COURRIEL.
   ► LE DEGRÉ N'EST PAS UN FILTRE ICI : il est seulement donné au
     Vénérable Maître. Un degré absent du registre est dit « non renseigné ».
═══════════════════════════════════════════════════════════════════ */

import { json, noter } from './_commun.js';
import { remettre, fournisseur, expediteur } from './_courriel.js';

const LOGE = 1;
const PAR_HEURE = 5;
const propre = v => String(v == null ? '' : v).trim();
const valable = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);

/* Tiré de joshua/corpus.json (ouvrages), sans lien, source ni degré. « Recueil intégral », « Guide de Survie »,
   « L'Alliance de Lumière », « Du Pétrin au Compas » et les documents de travail n'y figurent pas, à la demande du Souverain Grand Commandeur. */
const catalogue = [
  { id: "oved-1", titre: "RBI OVED — 1er degré complet" },
  { id: "boneh-2", titre: "RBI BONEH — 2e degré complet" },
  { id: "adon-3", titre: "RBI ADON — 3e degré complet" },
  { id: "tome-1", titre: "Tome I — rituel intégral (paginé)" },
  { id: "tome-2", titre: "Tome II — Loges de Perfection, rituels intégraux" },
  { id: "tome-3-rituels", titre: "Tome III — Les 22 Sentiers, rituels intégraux (11ᵉ–18ᵉ)" },
  { id: "tome-4", titre: "Tome IV — les Sentiers, grades 19ᵉ à 25ᵉ" },
  { id: "bible-du-rite", titre: "RBI — Bible du Rite, Tomes I & II" },
  { id: "bible-du-rite-t3", titre: "La Bible du Rite, Tome III — Les 22 Sentiers, grades 11ᵉ–18ᵉ" },
  { id: "trente-deux-voies", titre: "Les Trente-Deux Voies — Sefer Yetsirah commenté" },
  { id: "pirke-avot", titre: "Pirké Avot — édition RBI" },
  { id: "gadlu", titre: "GADLU, peux-tu répéter la question ?" },
  { id: "michlei-vekohelet", titre: "Michlei veKohelet (Proverbes et Ecclésiaste)" }
];

async function membre(context, courriel){
  const r = await context.env.DB.prepare('SELECT donnees FROM etat WHERE loge_id = ?').bind(LOGE).first();
  let etat = null; try { etat = r ? JSON.parse(r.donnees) : null; } catch (e) { return null; }
  return ((etat && etat.membres) || []).find(m => m &&
    propre(m.email).toLowerCase() === courriel && !['demission', 'radiation', 'decede', 'candidat'].includes(m.statut)) || null;
}

export async function onRequestPost(context){
  let c; try { c = await context.request.json(); } catch (e) { return json({ erreur: 'requete_illisible' }, 400); }
  const courriel = propre(c?.courriel).toLowerCase();
  if (!valable(courriel)) return json({ erreur: 'courriel_manquant' }, 400);
  const destinataire = propre(context.env.LIVRES_COURRIEL);
  if (!valable(destinataire)) return json({ erreur: 'non_configure' }, 503);

  const marque = 'livres : adresse inconnue';
  const essais = await context.env.DB.prepare("SELECT COUNT(*) AS n FROM journal WHERE loge_id = ? AND quoi LIKE 'livres :%' " +
    "AND le > datetime('now','-1 hour')").bind(LOGE).first().catch(() => null);
  if (Number(essais?.n ?? 0) >= 30) return json({ erreur: 'trop_dessais' }, 429);

  const m = await membre(context, courriel);
  if (!m){ await noter(context, LOGE, null, marque); return json({ erreur: 'inconnu' }, 404); }
  const degre = Number(m.degre) > 0 ? String(Number(m.degre)) : 'non renseigné';

  if (!c.livre) return json({ livres: catalogue.map(l => ({ id: l.id, titre: l.titre })) });

  const livre = catalogue.find(l => l.id === c.livre);
  if (!livre) return json({ erreur: 'livre_inconnu' }, 404);
  if (!fournisseur(context.env) || !expediteur(context.env).adresse) return json({ erreur: 'non_configure' }, 503);

  const nom = ((m.prenoms || '') + ' ' + (m.nom || '')).trim() || courriel;
  const corps = nom + ' (degré ' + degre + ' au registre, ' + courriel + ') demande le livre « ' + livre.titre + ' ».\n\n' +
    'À vous de voir s’il y a droit, puis l’impression et le paiement avec lui : répondez-lui à ' + courriel + '.';
  const sortie = await remettre(context.env, 'Demande de livre : ' + livre.titre, corps, [{ email: destinataire }]);
  const ok = sortie.configure && sortie.resultats.some(x => x.statut === 'partie');
  await noter(context, LOGE, null, 'livres : demande ' + livre.id + (ok ? ' envoyee' : ' refusee'));
  return ok ? json({ ok: true, livre: livre.titre }) : json({ erreur: 'envoi_refuse' }, 502);
}
