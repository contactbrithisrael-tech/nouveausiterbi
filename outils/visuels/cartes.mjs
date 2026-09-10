/* ═══════════════════════════════════════════════════════════════
   Définition des visuels à produire.

   Ce fichier ne contient que du contenu — aucun rendu. Pour ajouter
   une carte, ajouter une entrée ici et relancer le générateur : rien
   d'autre à modifier.

   Les textes proviennent des descriptions de l'auteur et des fiches
   KDP. Aucune formule n'a été inventée pour l'occasion.
════════════════════════════════════════════════════════════════ */

/* Formats de sortie. Le 1200×630 est celui que Facebook, LinkedIn et
   les aperçus de lien attendent ; le carré sert à Instagram et aux
   partages en messagerie. */
export const FORMATS = {
  paysage: { l: 1200, h: 630 },
  carre:   { l: 1080, h: 1080 }
};

export const LIVRES = {
  guide: {
    cle:      'BOOK_GUIDE',
    titre:    'Guide de Survie<br>pour Franc-Maçon Désemparé',
    sous:     'Démystification, résilience et sagesse au quotidien',
    meta:     '212 pages · Broché et Kindle',
    lien:     'brith-israel.org/livres.html'
  },
  petrin: {
    cle:      'BOOK_PETRIN',
    titre:    'Du Pétrin au Compas',
    sous:     'Quand on cherche un secret, on trouve une vérité',
    meta:     'Roman · Broché et Kindle',
    lien:     'brith-israel.org/livres.html'
  }
};

export const CARTES = [
  {
    id: 'citation-perfection', type: 'citation',
    texte: 'Arrêtez de chercher la perfection.<br>Elle est le tombeau<br>des bonnes volontés.',
    source: 'Guide de Survie pour Franc-Maçon Désemparé',
    formats: ['paysage', 'carre']
  },
  {
    id: 'citation-ombres', type: 'citation',
    texte: 'Et si la plus grande des initiations<br>n\'était pas la lumière,<br>mais l\'art de vivre avec ses ombres ?',
    source: 'Guide de Survie pour Franc-Maçon Désemparé',
    formats: ['paysage', 'carre']
  },
  {
    id: 'citation-verite', type: 'citation',
    texte: 'On cherche un secret,<br>on trouve une vérité.<br><em>Sa</em> vérité. Pas <em>la</em> vérité.',
    source: 'Du Pétrin au Compas',
    formats: ['paysage', 'carre']
  },
  {
    id: 'citation-loge', type: 'citation',
    texte: 'Ce n\'était pas ce qu\'elle croyait.<br>C\'était une loge maçonnique.',
    source: 'Du Pétrin au Compas',
    formats: ['paysage', 'carre']
  },
  {
    /* L'argument le plus distinctif de l'auteur, et le seul qu'aucun
       autre livre du rayon ne peut reprendre. */
    id: 'auteur-parcours', type: 'auteur',
    lignes: [
      'Né grand prématuré de 900 grammes.',
      'Rescapé d\'un coma à six ans.',
      'Pâtissier, puis docteur en médecine<br>traditionnelle chinoise à Shanghai.',
      'Militaire de réserve, expert en secourisme.'
    ],
    chute: 'Il n\'écrit pas depuis une tour d\'ivoire mystique.<br>Il écrit depuis le terrain.',
    nom: 'Mickaël Darmon',
    formats: ['paysage', 'carre']
  },
  {
    /* La formule de l'auteur, relevée dans sa propre bio Facebook.
       C'est la meilleure accroche du corpus, et elle ne figurait
       nulle part ailleurs. */
    id: 'citation-en-loge', type: 'citation',
    texte: 'Un livre qui dit ce qu\'on ne dit pas en loge.',
    source: 'Guide de Survie pour Franc-Maçon Désemparé',
    formats: ['paysage', 'carre']
  },
  {
    id: 'citation-silence', type: 'citation',
    texte: 'Apprendre à s\'effacer<br>pour laisser passer la lumière.',
    source: 'Guide de Survie pour Franc-Maçon Désemparé',
    formats: ['paysage', 'carre']
  },
  {
    id: 'citation-etoile', type: 'citation',
    texte: 'Une étoile jaune tachée de sang,<br>une judéité cachée depuis la guerre.',
    source: 'Du Pétrin au Compas',
    formats: ['paysage', 'carre']
  },
  { id: 'livre-guide',  type: 'livre', livre: 'guide',  formats: ['paysage', 'carre'] },
  { id: 'livre-petrin', type: 'livre', livre: 'petrin', formats: ['paysage', 'carre'] }
];
