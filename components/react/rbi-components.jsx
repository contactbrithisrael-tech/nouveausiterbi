/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — composants React isolés
   Fichier UNIQUE, sans dépendance autre que React.

   ── POURQUOI UN SEUL FICHIER, ET AUCUN IMPORT CSS ───────────
   Un `import './styles.css'` n'est compréhensible que par un
   bundler (Vite, webpack, Next). Ces composants doivent pouvoir être
   déposés tels quels dans n'importe quel projet — y compris une page
   qui charge React par balise <script> (voir components/demo.html).
   Les styles sont donc une CHAÎNE injectée une seule fois par
   `useStylesRbi()`. Le prix à payer est modeste ; le gain est qu'il
   n'existe aucune étape de build obligatoire.

   ── ISOLATION ────────────────────────────────────────────────
   Mêmes règles que les composants HTML : préfixe `rbi-`, variables
   de thème portées par la racine de chaque composant (surchargeables
   par la prop `theme`), aucune police distante, aucun style global.

   ── DONNÉES ──────────────────────────────────────────────────
   Chaque composant accepte ses données en props avec des valeurs par
   défaut tirées du site. Un projet peut donc les alimenter depuis le
   pont Make.com (tools/make-bridge.js, action « content.get ») sans
   modifier une ligne de ce fichier.

   Usage (avec bundler) :
     import { RbiHero, RbiChefCard, RbiBookCard, RbiTuilage } from './rbi-components.jsx';
   Usage (sans bundler) : voir components/demo.html
════════════════════════════════════════════════════════════════ */
import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';

/* ── Styles ─────────────────────────────────────────────────────
   Une seule balise <style> pour tous les composants, insérée à la
   première utilisation et JAMAIS retirée : plusieurs composants la
   partagent, et la retirer au démontage de l'un casserait les autres.
   L'idempotence repose sur un `id` : un second appel ne fait rien. */
const STYLE_ID = 'rbi-composants-styles';

const CSS = `
.rbi-c {
  --rbi-or: #C9A84C; --rbi-or-clair: #E8C96A; --rbi-noir: #0d0d0d;
  --rbi-noir-2: #1a1a1a; --rbi-blanc: #F5F0E8; --rbi-rouge: #b4544a;
  --rbi-titre: 'Cinzel', 'Trajan Pro', Georgia, 'Times New Roman', serif;
  --rbi-corps: 'EB Garamond', Georgia, 'Times New Roman', serif;
  box-sizing: border-box; color: var(--rbi-blanc); font-family: var(--rbi-corps); line-height: 1.6;
}
.rbi-c *, .rbi-c *::before, .rbi-c *::after { box-sizing: border-box; margin: 0; padding: 0; }
.rbi-c button, .rbi-c input { font: inherit; color: inherit; }

/* — Hero — */
.rbi-c--hero { position: relative; isolation: isolate; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; min-height: 420px; padding: 3rem 1.5rem; text-align: center; background: radial-gradient(ellipse at 50% 30%, #14120c 0%, #080808 65%); overflow: hidden; }
.rbi-c--hero::before { content: ''; position: absolute; inset: 0; z-index: -1; background-image:
  radial-gradient(1.4px 1.4px at 20% 30%, rgba(245,240,232,.75) 50%, transparent 51%),
  radial-gradient(1px 1px at 70% 20%, rgba(245,240,232,.55) 50%, transparent 51%),
  radial-gradient(1.6px 1.6px at 45% 75%, rgba(201,168,76,.55) 50%, transparent 51%);
  background-size: 240px 240px, 180px 180px, 320px 320px; animation: rbi-scintille 5s ease-in-out infinite alternate; }
@keyframes rbi-scintille { from { opacity: .45; } to { opacity: 1; } }
.rbi-c__bandeau { font-family: var(--rbi-titre); font-size: .75rem; letter-spacing: .22em; color: var(--rbi-or); margin-bottom: 1.5rem; }
.rbi-c__sceau { width: 110px; height: 110px; object-fit: contain; margin-bottom: 1.2rem; }
.rbi-c__h1 { font-family: var(--rbi-titre); font-size: clamp(1.8rem, 5vw, 3rem); letter-spacing: .05em; line-height: 1.2; }
.rbi-c__he { display: block; font-size: clamp(1.2rem, 3.5vw, 2rem); color: var(--rbi-or); margin-top: .4rem; }
.rbi-c__sous { max-width: 640px; margin: 1.1rem auto 0; color: #cfc9bd; }
.rbi-c__sous em { display: block; margin-top: .4rem; font-size: .92rem; color: #a8a298; }
.rbi-c__cta { display: flex; flex-wrap: wrap; gap: .75rem; justify-content: center; margin-top: 1.8rem; }

/* — Boutons partagés — */
.rbi-c__btn { display: inline-block; padding: .6rem 1.3rem; font-family: var(--rbi-titre); font-size: .74rem; letter-spacing: .13em; text-transform: uppercase; text-decoration: none; border: 1px solid var(--rbi-or); border-radius: 2px; cursor: pointer; transition: background .25s ease, color .25s ease; }
.rbi-c__btn--plein { background: var(--rbi-or); color: var(--rbi-noir); }
.rbi-c__btn--vide { background: transparent; color: var(--rbi-or); }
.rbi-c__btn--plein:hover { background: var(--rbi-or-clair); }
.rbi-c__btn--vide:hover { background: rgba(201,168,76,.12); }
.rbi-c__btn:focus-visible { outline: 2px solid var(--rbi-or-clair); outline-offset: 2px; }

/* — Carte dignitaire — */
.rbi-c--chef { display: inline-block; width: 100%; max-width: 320px; padding: 1.75rem 1.25rem; text-align: center; background: linear-gradient(180deg, var(--rbi-noir-2) 0%, var(--rbi-noir) 100%); border: 1px solid rgba(201,168,76,.28); border-radius: 4px; contain: layout style; }
.rbi-c__photo-wrap { position: relative; width: 130px; height: 130px; margin: 0 auto 1rem; border-radius: 50%; overflow: hidden; border: 2px solid var(--rbi-or); background: var(--rbi-noir-2); }
.rbi-c__photo { width: 100%; height: 100%; object-fit: cover; display: block; position: relative; z-index: 2; }
.rbi-c__ph { position: absolute; inset: 0; z-index: 1; display: flex; align-items: center; justify-content: center; font-family: var(--rbi-titre); font-size: 3rem; color: var(--rbi-or); }
.rbi-c__grade { display: inline-block; padding: .2rem .75rem; margin-bottom: .6rem; font-family: var(--rbi-titre); font-size: .72rem; letter-spacing: .14em; color: var(--rbi-noir); background: var(--rbi-or); border-radius: 2px; }
.rbi-c__nom { font-family: var(--rbi-titre); font-size: 1.05rem; letter-spacing: .06em; margin-bottom: .35rem; }
.rbi-c__role-titre { font-size: .9rem; color: var(--rbi-or-clair); font-style: italic; }
.rbi-c__role { font-size: .82rem; color: #9a9a9a; margin-top: .3rem; }

/* — Fiche livre — */
.rbi-c--livre { display: block; width: 100%; max-width: 640px; background: var(--rbi-noir); border: 1px solid rgba(201,168,76,.28); border-radius: 4px; overflow: hidden; container-type: inline-size; container-name: rbi-livre; }
.rbi-c__livre-grille { display: grid; grid-template-columns: 180px 1fr; gap: 1.25rem; padding: 1.25rem; align-items: start; }
@container rbi-livre (max-width: 480px) { .rbi-c__livre-grille { grid-template-columns: 1fr; } }
@supports not (container-type: inline-size) { @media (max-width: 480px) { .rbi-c__livre-grille { grid-template-columns: 1fr; } } }
.rbi-c__cover { position: relative; aspect-ratio: 2/3; background: var(--rbi-noir-2); border: 1px solid rgba(201,168,76,.25); border-radius: 3px; overflow: hidden; }
.rbi-c__cover .rbi-c__ph { font-size: 3.5rem; color: rgba(201,168,76,.55); }
.rbi-c__titre-livre { font-family: var(--rbi-titre); font-size: 1.15rem; letter-spacing: .04em; }
.rbi-c__sous-livre { font-size: .85rem; color: var(--rbi-or-clair); font-style: italic; margin: .2rem 0 .6rem; }
.rbi-c__desc { font-size: .92rem; color: #b9b4aa; }
.rbi-c__liens { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .9rem; }

/* — Tuilage — */
.rbi-c--tuilage { display: block; width: 100%; max-width: 560px; padding: 2rem 1.5rem; text-align: center; background: radial-gradient(ellipse at top, var(--rbi-noir-2) 0%, var(--rbi-noir) 70%); border: 1px solid rgba(201,168,76,.3); border-radius: 4px; }
.rbi-c__question { font-family: var(--rbi-titre); font-size: 1.05rem; margin-bottom: .9rem; }
.rbi-c__saisie { display: flex; gap: .5rem; flex-wrap: wrap; justify-content: center; }
.rbi-c__input { flex: 1 1 220px; min-width: 0; padding: .6rem .85rem; background: rgba(0,0,0,.45); border: 1px solid rgba(201,168,76,.4); border-radius: 2px; }
.rbi-c__input:focus { outline: 2px solid var(--rbi-or); outline-offset: 1px; }
.rbi-c__retour { min-height: 1.4rem; margin-top: .7rem; font-size: .88rem; }
.rbi-c__retour[data-type="ok"] { color: var(--rbi-or-clair); }
.rbi-c__retour[data-type="error"] { color: var(--rbi-rouge); }
.rbi-c__icone { display: block; font-size: 2.2rem; color: var(--rbi-or); margin-bottom: .5rem; }

@media (prefers-reduced-motion: reduce) {
  .rbi-c--hero::before { animation: none; opacity: .7; }
  .rbi-c *, .rbi-c *::before { transition: none !important; }
}
`;

function useStylesRbi() {
  /* useEffect et non un effet de module : l'injection doit avoir lieu
     dans le document du navigateur, pas à l'évaluation du module — ce
     dernier peut être chargé côté serveur (Next.js), où `document`
     n'existe pas. La garde ci-dessous rend le composant compatible
     avec un rendu serveur sans configuration particulière. */
  useEffect(() => {
    if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }, []);
}

/* Thème : converti en variables CSS inline sur la racine du composant.
   Passer par des variables plutôt que par des styles calculés permet à
   une feuille de style hôte de surcharger le thème sans avoir à lutter
   contre la spécificité d'un style inline sur chaque élément. */
function varsTheme(theme) {
  if (!theme) return undefined;
  return Object.fromEntries(Object.entries(theme).map(([k, v]) => [`--rbi-${k}`, v]));
}

/* Image avec repli : le placeholder n'est PAS conditionné à l'absence
   de `src` seulement, mais aussi à l'échec de chargement (`onError`).
   Une URL présente mais morte laisserait sinon un cadre vide — cas
   fréquent quand les visuels sont servis par un tiers. */
function ImageOuInitiale({ src, alt, initiale, className }) {
  const [echoue, setEchoue] = useState(false);
  const montrerImage = Boolean(src) && !echoue;
  return (
    <>
      {montrerImage && (
        <img className={className} src={src} alt={alt} onError={() => setEchoue(true)} loading="lazy" />
      )}
      {!montrerImage && <span className="rbi-c__ph" aria-hidden="true">{initiale}</span>}
    </>
  );
}

/* ── HERO ───────────────────────────────────────────────────── */
export function RbiHero({
  bandeau = "A∴L∴G∴G∴A∴D∴L'∴U∴ — ב∴ס∴ד∴",
  titreFr = 'Rite Brith Israël',
  titreHe = 'ברית ישראל',
  sceau = '',
  sousTitre = 'Rite Maçonnique Historique d’inspiration Kabbalistique en 33 degrés.',
  sousTitre2 = 'Alliance de Lumière entre les Peuples, fidélité à la Tradition Hébraïque, universalité de la Franc-Maçonnerie.',
  actions = [
    { label: 'Découvrir le Rite', href: 'https://www.brith-israel.org/#rite', style: 'plein' },
    { label: 'Devenir Franc-Maçon', href: 'https://www.brith-israel.org/devenir-fm.html', style: 'vide' }
  ],
  theme
}) {
  useStylesRbi();
  return (
    <section className="rbi-c rbi-c--hero" style={varsTheme(theme)}>
      <p className="rbi-c__bandeau">{bandeau}</p>
      {sceau && <img className="rbi-c__sceau" src={sceau} alt={`Sceau — ${titreFr}`} />}
      <h1 className="rbi-c__h1">
        {titreFr}
        {/* lang et dir portés par l'élément hébreu seul : mêler les
            directions sur le parent déplacerait la ponctuation latine. */}
        <span className="rbi-c__he" dir="rtl" lang="he">{titreHe}</span>
      </h1>
      <p className="rbi-c__sous">{sousTitre}<em>{sousTitre2}</em></p>
      <div className="rbi-c__cta">
        {actions.map((a, i) => (
          <a key={a.href || i} className={`rbi-c__btn rbi-c__btn--${a.style || 'plein'}`}
             href={a.href} target="_blank" rel="noopener noreferrer">{a.label}</a>
        ))}
      </div>
    </section>
  );
}

/* ── CARTE DIGNITAIRE ───────────────────────────────────────── */
export function RbiChefCard({ nom = 'T∴I∴F∴ Mickaël DARMON', grade = '33°-96°', titre = 'Souverain Grand Commandeur', role = 'Fondateur et Grand Maître', photo = '', onClick, theme }) {
  useStylesRbi();
  const interactif = typeof onClick === 'function';
  return (
    /* Une carte cliquable devient un vrai contrôle : `role`, `tabIndex`
       et la touche Entrée. Un <div onClick> nu est invisible au clavier
       et aux technologies d'assistance — inacceptable pour un composant
       destiné à être réutilisé dans des contextes inconnus. */
    <div
      className="rbi-c rbi-c--chef"
      style={{ ...varsTheme(theme), cursor: interactif ? 'pointer' : undefined }}
      onClick={onClick}
      onKeyDown={interactif ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(e); } } : undefined}
      role={interactif ? 'button' : undefined}
      tabIndex={interactif ? 0 : undefined}
    >
      <div className="rbi-c__photo-wrap">
        <ImageOuInitiale src={photo} alt={`Portrait de ${nom}`} initiale={nom.charAt(0)} className="rbi-c__photo" />
      </div>
      <span className="rbi-c__grade">{grade}</span>
      <h3 className="rbi-c__nom">{nom}</h3>
      <p className="rbi-c__role-titre">{titre}</p>
      <p className="rbi-c__role">{role}</p>
    </div>
  );
}

/* ── FICHE LIVRE ────────────────────────────────────────────── */
export function RbiBookCard({ titre = "L'Alliance de Lumière", sous = 'Tome I — Rituel du Rite Brith Israël', desc = 'Le premier tome des rituels du Rite Brith Israël, publié aux éditions CoolLibri.', couverture = '', placeholder = 'L', liens = [{ label: 'CoolLibri', url: 'https://www.coollibri.com', style: 'plein' }], theme }) {
  useStylesRbi();
  return (
    <div className="rbi-c rbi-c--livre" style={varsTheme(theme)}>
      <div className="rbi-c__livre-grille">
        <div className="rbi-c__cover">
          <ImageOuInitiale src={couverture} alt={`Couverture de ${titre}`} initiale={placeholder} className="rbi-c__photo" />
        </div>
        <div>
          <h3 className="rbi-c__titre-livre">{titre}</h3>
          <p className="rbi-c__sous-livre">{sous}</p>
          <p className="rbi-c__desc">{desc}</p>
          <div className="rbi-c__liens">
            {liens.map((l, i) => (
              <a key={l.url || i} className={`rbi-c__btn rbi-c__btn--${l.style || 'plein'}`}
                 href={l.url} target="_blank" rel="noopener noreferrer">{l.label}</a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── TUILAGE ────────────────────────────────────────────────── */
export const QUESTIONS_PAR_DEFAUT = [
  { id: 'q1', texte: "D'où venez-vous ?", reponses: ['de saint jean', 'saint jean', 'loge de saint jean', 'de la loge saint jean'] },
  { id: 'q2', texte: 'Quel âge avez-vous ?', reponses: ['3 ans', '5 ans', '7 ans', 'trois ans', 'cinq ans', 'sept ans', '3', '5', '7'] }
];

/* Normalisation identique à celle du site et du pont Make.com.
   Exportée pour qu'un projet consommateur puisse la réutiliser plutôt
   que d'en écrire une variante — trois normalisations divergentes
   produiraient trois verdicts différents pour la même réponse. */
export function normaliseReponse(s) {
  return (s || '').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ').trim();
}

export function RbiTuilage({
  titre = 'Tuilage Maçonnique',
  intro = 'Frère, avant d’accéder aux documents réservés, veuillez répondre aux questions de tuilage.',
  questions = QUESTIONS_PAR_DEFAUT,
  maxEssais = 3,
  delaiMs = 900,
  succes = { icone: '✡', titre: 'Frère reconnu', message: 'M∴T∴C∴S∴ — Que la Lumière vous guide.' },
  echec = { message: 'Je ne saurais vous reconnaître, Profane.' },
  /* Point d'extension : permet de déléguer le verdict au pont
     Make.com (action « tuilage.verify ») au lieu de le calculer dans
     le navigateur. La signature est asynchrone dans les deux cas, pour
     que le composant n'ait pas à savoir lequel est en place. */
  onVerifier,
  onSucces,
  theme
}) {
  useStylesRbi();
  const [etape, setEtape] = useState('start');     // start | index de question | succes | echec
  const [essais, setEssais] = useState(() => questions.map(() => 0));
  const [valeur, setValeur] = useState('');
  const [retour, setRetour] = useState({ texte: '', type: null });
  const champRef = useRef(null);
  const minuteries = useRef([]);

  /* Toutes les minuteries sont mémorisées puis annulées au démontage :
     un setTimeout qui survit au composant appellerait setState sur un
     élément démonté — fuite mémoire et avertissement React. */
  useEffect(() => () => { minuteries.current.forEach(clearTimeout); }, []);
  const differer = useCallback((fn, ms) => { minuteries.current.push(setTimeout(fn, ms)); }, []);

  const indexCourant = typeof etape === 'number' ? etape : null;
  const question = indexCourant !== null ? questions[indexCourant] : null;

  useEffect(() => { if (question && champRef.current) champRef.current.focus(); }, [question]);

  const verifierLocalement = useCallback(async (q, saisie) => {
    const val = normaliseReponse(saisie);
    return val !== '' && (q.reponses || []).some((r) => normaliseReponse(r) === val);
  }, []);

  const valider = useCallback(async () => {
    if (!question) return;
    const juger = onVerifier || verifierLocalement;
    const ok = await juger(question, valeur);
    if (ok) {
      setRetour({ texte: 'Bien répondu, Frère.', type: 'ok' });
      differer(() => {
        setValeur('');
        setRetour({ texte: '', type: null });
        if (indexCourant + 1 < questions.length) setEtape(indexCourant + 1);
        else { setEtape('succes'); if (onSucces) onSucces(); }
      }, delaiMs);
      return;
    }
    /* Compteur par question, comme sur le site : une erreur sur la
       première ne doit pas consommer le crédit de la suivante. */
    const suivants = essais.slice();
    suivants[indexCourant] += 1;
    setEssais(suivants);
    if (suivants[indexCourant] >= maxEssais) { setEtape('echec'); return; }
    setRetour({ texte: `Je ne vous reconnais pas. Essai ${suivants[indexCourant]}/${maxEssais}.`, type: 'error' });
    setValeur('');
  }, [question, valeur, onVerifier, verifierLocalement, differer, indexCourant, questions.length, essais, maxEssais, delaiMs, onSucces]);

  const recommencer = useCallback(() => {
    setEssais(questions.map(() => 0));
    setValeur('');
    setRetour({ texte: '', type: null });
    setEtape('start');
  }, [questions]);

  const style = useMemo(() => varsTheme(theme), [theme]);

  return (
    <div className="rbi-c rbi-c--tuilage" style={style}>
      <h3 className="rbi-c__nom" style={{ color: 'var(--rbi-or)' }}>{titre}</h3>
      <p className="rbi-c__desc" style={{ marginBottom: '1.4rem' }}>{intro}</p>

      {etape === 'start' && (
        <button type="button" className="rbi-c__btn rbi-c__btn--plein" onClick={() => setEtape(0)}>
          Commencer le Tuilage
        </button>
      )}

      {question && (
        /* <form onSubmit> plutôt qu'un bouton seul : la touche Entrée
           fonctionne alors nativement, y compris sur les claviers
           mobiles où elle est étiquetée « OK » ou « Valider ». */
        <form onSubmit={(e) => { e.preventDefault(); valider(); }}>
          <p className="rbi-c__question">{question.texte}</p>
          <div className="rbi-c__saisie">
            <input
              ref={champRef}
              className="rbi-c__input"
              type="text"
              value={valeur}
              autoComplete="off"
              aria-label={question.texte}
              placeholder="Votre réponse…"
              onChange={(e) => setValeur(e.target.value)}
            />
            <button type="submit" className="rbi-c__btn rbi-c__btn--plein">Répondre</button>
          </div>
          {/* aria-live : le retour est annoncé aux lecteurs d'écran,
              qui ne perçoivent aucun changement de texte silencieux. */}
          <p className="rbi-c__retour" data-type={retour.type || undefined} aria-live="polite">{retour.texte}</p>
        </form>
      )}

      {etape === 'succes' && (
        <div>
          <span className="rbi-c__icone">{succes.icone}</span>
          <h4 className="rbi-c__question">{succes.titre}</h4>
          <p className="rbi-c__desc">{succes.message}</p>
        </div>
      )}

      {etape === 'echec' && (
        <div>
          <span className="rbi-c__icone">✕</span>
          <p className="rbi-c__desc" style={{ marginBottom: '1rem' }}>{echec.message}</p>
          <button type="button" className="rbi-c__btn rbi-c__btn--vide" onClick={recommencer}>Recommencer</button>
        </div>
      )}
    </div>
  );
}

export default { RbiHero, RbiChefCard, RbiBookCard, RbiTuilage, normaliseReponse, QUESTIONS_PAR_DEFAUT };
