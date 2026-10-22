/* ═══════════════════════════════════════════════════════════════════
   FUSIONNER DEUX TRAVAUX, AU LIEU D'EN REFUSER UN

   CE QUI SE PASSAIT. Le registre s'écrivait en bloc : chaque
   enregistrement remettait TOUT le document, avec le numéro de version
   sur lequel il se fondait. Si quelqu'un avait écrit entre-temps, le
   serveur refusait, et le programme posait cette question :

     « Quelqu'un d'autre a enregistré pendant que vous travailliez.
       OK : je reprends la version du registre — ce qui n'est que sur
       cet appareil sera perdu. »

   Autrement dit : à deux, l'un des deux perd son travail. La Sœur
   Secrétaire note un téléphone pendant que le Trésorier saisit un
   règlement, et l'un des deux recommence. Ce n'est pas une panne, c'est
   la conséquence d'écrire en bloc — et cela rend le travail à deux
   impossible, ce qui était pourtant la raison d'être du serveur.

   CE QUI SE FAIT MAINTENANT. On ne compare plus deux documents, on en
   compare TROIS :

     — LE SOCLE : le document tel qu'il était quand celui qui écrit a
       commencé. Son programme l'avait déjà, il le renvoie avec.
     — LE LEUR : ce que porte le registre à cet instant.
     — LE MIEN : ce que celui qui écrit veut poser.

   Avec trois, on sait QUI A CHANGÉ QUOI, et non plus seulement que
   deux choses diffèrent. Un champ que je n'ai pas touché garde la
   valeur de l'autre ; un champ que l'autre n'a pas touché prend la
   mienne. Les deux travaux tiennent.

   ► POURQUOI LE SOCLE VIENT DU PROGRAMME, ET NON DE LA BASE. Le
     serveur pourrait garder un historique. Cela voudrait dire une
     table de plus, donc un fichier SQL à jouer à la main sur la base
     en service. Le programme, lui, a déjà le socle sous la main : il
     vient de le recevoir. Le renvoyer ne coûte rien et n'oblige
     personne à ouvrir un tableau de bord.

     On ne lui fait pas confiance pour autant : le socle ne sert qu'à
     deviner qui a changé quoi. Quelqu'un qui le fausserait n'obtient
     rien qu'il n'obtiendrait déjà en écrivant ce qu'il veut — il a une
     session, c'est son registre.

   ► CE QUE LA FUSION NE SAIT PAS FAIRE. Quand les DEUX ont changé le
     MÊME champ, aucune règle ne devine lequel a raison. Le dernier qui
     écrit l'emporte — et on l'écrit au journal, avec le chemin du
     champ. Un arbitrage qu'on ne voit pas est un arbitrage qui se
     découvre trop tard.
═══════════════════════════════════════════════════════════════════ */

const estObjet = v => v !== null && typeof v === 'object';
const estTableau = Array.isArray;

/* Égalité de valeurs, non de références : ce qu'on compare vient de
   deux JSON.parse différents, et deux objets identiques n'y sont jamais
   le même objet. */
function pareil(a, b){
  if (a === b) return true;
  if (!estObjet(a) || !estObjet(b)) return false;
  try { return JSON.stringify(a) === JSON.stringify(b); } catch (e) { return false; }
}

/* ── UN TABLEAU DE FICHES N'EST PAS UNE LISTE DE CASES ──────────────
   Fusionner deux tableaux case par case est faux dès que quelqu'un
   insère ou retire : tout ce qui suit se décale, et l'on recolle le
   téléphone d'un Frère sur la fiche d'un autre.

   Les tableaux de ce registre — membres, visiteurs, Loges amies, Amis,
   convocations — portent tous un « id ». On les fusionne donc PAR ID,
   et l'ordre n'a plus d'importance. Un tableau sans id (une liste de
   mots, le journal) se traite comme une valeur simple. */
const parId = l => estTableau(l) && l.length > 0 &&
  l.every(x => estObjet(x) && !estTableau(x) &&
               (typeof x.id === 'number' || typeof x.id === 'string'));

function index(l){
  const m = new Map();
  for (const x of (l || [])) m.set(String(x.id), x);
  return m;
}

/* ── LA FUSION ──────────────────────────────────────────────────────
   Rend le document fusionné. « ecrases » recueille le chemin des
   champs où les deux avaient changé : ce sont les seuls endroits où
   l'on a dû trancher, et ils doivent se dire.

   « absent » distingue « la clé n'existait pas » de « la clé vaut
   null » : sans quoi, effacer une valeur et ne jamais l'avoir écrite
   seraient la même chose, et l'on ne saurait pas honorer un effacement. */
const ABSENT = Symbol('absent');

export function fusionner(socle, leur, mien, ecrases = [], chemin = []){
  /* Rien à arbitrer : les deux côtés disent la même chose. */
  if (pareil(leur, mien)) return mien;

  const mienBouge = !pareil(mien, socle);
  const leurBouge = !pareil(leur, socle);

  /* Un seul des deux a touché : c'est lui qui décide, sans discussion. */
  if (!mienBouge) return leur;
  if (!leurBouge) return mien;

  /* Les deux ont touché. Si ce sont deux fiches, on descend dedans :
     le désaccord est peut-être sur des champs différents.

     UNE FICHE QUI N'EXISTAIT PAS AU SOCLE SE FUSIONNE QUAND MÊME. Deux
     Officiers peuvent avoir ajouté la même fiche chacun de son côté —
     même numéro, renseignements différents. Sans cette ligne, le socle
     absent faisait tomber le cas dans « le dernier l'emporte », et la
     moitié du travail partait. Un socle absent vaut donc : rien
     n'existait, et tout ce que chacun a écrit est un ajout. */
  if (estObjet(leur) && estObjet(mien)){
    if (socle === ABSENT || !estObjet(socle))
      socle = (estTableau(leur) || estTableau(mien)) ? [] : {};

    if (parId(leur) || parId(mien)){
      const iS = index(estTableau(socle) ? socle : []);
      const iL = index(estTableau(leur) ? leur : []);
      const iM = index(estTableau(mien) ? mien : []);
      const sortie = [];
      const vus = new Set();
      /* L'ordre de celui qui écrit d'abord, puis ce que l'autre a
         ajouté : on ne réordonne pas le travail de quelqu'un. */
      for (const x of (estTableau(mien) ? mien : [])){
        const k = String(x.id); vus.add(k);
        /* Retirée par l'autre alors qu'elle existait au socle : son
           retrait est un acte, on l'honore. */
        if (iS.has(k) && !iL.has(k)) continue;
        sortie.push(iL.has(k)
          ? fusionner(iS.get(k) ?? ABSENT, iL.get(k), x, ecrases, chemin.concat(k))
          : x);
      }
      for (const y of (estTableau(leur) ? leur : [])){
        const k = String(y.id);
        if (vus.has(k)) continue;
        /* Retirée par celui qui écrit : même raison, en sens inverse. */
        if (iS.has(k) && !iM.has(k)) continue;
        sortie.push(y);
      }
      return sortie;
    }

    /* Deux tableaux sans id : on ne sait pas les apparier. Celui qui
       écrit l'emporte, et on le dit. */
    if (estTableau(leur) || estTableau(mien)){
      ecrases.push(chemin.join('.') || '(racine)');
      return mien;
    }

    /* Deux fiches : clé par clé, sur l'union des clés. */
    const sortie = {};
    const cles = new Set([...Object.keys(leur), ...Object.keys(mien)]);
    for (const c of cles){
      const s = estObjet(socle) && !estTableau(socle) && c in socle ? socle[c] : ABSENT;
      const l = c in leur ? leur[c] : ABSENT;
      const m = c in mien ? mien[c] : ABSENT;
      /* Une clé retirée d'un côté et inchangée de l'autre : on honore
         le retrait. Retirée des deux : elle ne revient pas. */
      if (l === ABSENT && m === ABSENT) continue;
      if (l === ABSENT){ if (!pareil(m, s)) sortie[c] = m; continue; }
      if (m === ABSENT){
        /* Je l'ai retirée, l'autre l'a modifiée. Honorer mon retrait
           perdrait sa modification ; garder la sienne perd mon
           retrait. On garde la sienne — une valeur écrite dit plus
           qu'une clé absente — et on consigne l'arbitrage. */
        if (!pareil(l, s)){ ecrases.push(chemin.concat(c).join('.')); sortie[c] = l; }
        continue;
      }
      sortie[c] = fusionner(s, l, m, ecrases, chemin.concat(c));
    }
    return sortie;
  }

  /* Deux valeurs simples, toutes deux changées, et différentes : le
     dernier qui écrit l'emporte. C'est le seul endroit où quelque
     chose se perd, et c'est le seul endroit qu'on consigne. */
  ecrases.push(chemin.join('.') || '(racine)');
  return mien;
}
