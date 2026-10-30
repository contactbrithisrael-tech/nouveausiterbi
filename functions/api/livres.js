/* ═══════════════════════════════════════════════════════════════════
   DEMANDER UN LIVRE DU RITE, À SON DEGRÉ

   Un membre donne l'adresse de ses convocations. Le serveur le
   reconnaît au registre, lit SON DEGRÉ, et ne lui propose que les
   ouvrages dont le plus haut degré ne dépasse pas le sien. Sa demande
   part par courriel au Vénérable Maître Jean-Michel RAUX, qui règle
   avec lui l'impression et le paiement. Le courriel dit qui demande
   quoi, et rien d'autre.

   ► LA LISTE VIENT DU CORPUS (joshua/corpus.json), par identifiants
     choisis ci-dessous. N'en sortent ni lien Drive ni source : un
     titre, un degré.
   ► LE DESTINATAIRE N'EST PAS DANS CE FICHIER : le dépôt est servi en
     clair. Il vit dans le secret Cloudflare LIVRES_COURRIEL.
   ► UN DEGRÉ INCONNU N'OUVRE RIEN D'AU-DELÀ DU DEGRÉ ZÉRO. On ne
     devine pas le degré d'un membre.
═══════════════════════════════════════════════════════════════════ */

import { json, noter } from './_commun.js';
import { remettre, fournisseur, expediteur } from './_courriel.js';

const LOGE = 1;
const PAR_HEURE = 5;
const propre = v => String(v == null ? '' : v).trim();
const valable = a => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(a);

/* Tiré de joshua/corpus.json (ouvrages), sans lien ni source. « Recueil intégral », « Guide de Survie »,
   « L'Alliance de Lumière », « Du Pétrin au Compas » et les documents de travail n'y figurent pas, à la demande du Souverain Grand Commandeur. */
const catalogue = [
  { id: "oved-1", titre: "RBI OVED — 1er degré complet", degre_max: 1 },
  { id: "boneh-2", titre: "RBI BONEH — 2e degré complet", degre_max: 2 },
  { id: "adon-3", titre: "RBI ADON — 3e degré complet", degre_max: 3 },
  { id: "tome-1", titre: "Tome I — rituel intégral (paginé)", degre_max: 3 },
  { id: "tome-2", titre: "Tome II — Loges de Perfection, rituels intégraux", degre_max: 10 },
  { id: "tome-3-rituels", titre: "Tome III — Les 22 Sentiers, rituels intégraux (11ᵉ–18ᵉ)", degre_max: 18 },
  { id: "tome-4", titre: "Tome IV — les Sentiers, grades 19ᵉ à 25ᵉ", degre_max: 25 },
  { id: "bible-du-rite", titre: "RBI — Bible du Rite, Tomes I & II", degre_max: 10 },
  { id: "bible-du-rite-t3", titre: "La Bible du Rite, Tome III — Les 22 Sentiers, grades 11ᵉ–18ᵉ", degre_max: 18 },
  { id: "trente-deux-voies", titre: "Les Trente-Deux Voies — Sefer Yetsirah commenté", degre_max: 32 },
  { id: "pirke-avot", titre: "Pirké Avot — édition RBI", degre_max: 1 }
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
  const degre = Number(m.degre) > 0 ? Number(m.degre) : 0;
  const permis = catalogue.filter(l => l.degre_max <= degre);

  if (!c.livre) return json({ degre, livres: permis.map(l => ({ id: l.id, titre: l.titre })) });

  const livre = permis.find(l => l.id === c.livre);
  if (!livre) return json({ erreur: 'livre_interdit' }, 403);
  if (!fournisseur(context.env) || !expediteur(context.env).adresse) return json({ erreur: 'non_configure' }, 503);

  const nom = ((m.prenoms || '') + ' ' + (m.nom || '')).trim() || courriel;
  const corps = nom + ' (degré ' + degre + ', ' + courriel + ') demande le livre « ' + livre.titre + ' ».\n\n' +
    'L’impression et le paiement sont à voir avec lui : répondez-lui à ' + courriel + '.';
  const sortie = await remettre(context.env, 'Demande de livre : ' + livre.titre, corps, [{ email: destinataire }]);
  const ok = sortie.configure && sortie.resultats.some(x => x.statut === 'partie');
  await noter(context, LOGE, null, 'livres : demande ' + livre.id + (ok ? ' envoyee' : ' refusee'));
  return ok ? json({ ok: true, livre: livre.titre }) : json({ erreur: 'envoi_refuse' }, 502);
}
