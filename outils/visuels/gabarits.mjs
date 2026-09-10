/* ═══════════════════════════════════════════════════════════════
   Gabarits HTML des visuels.

   Les couleurs et la typographie reprennent celles du site. Les
   polices sont celles du conteneur (DejaVu Serif) : aucune police
   n'est chargée depuis le réseau, pour que le rendu soit identique
   à chaque exécution, hors ligne comprise.
════════════════════════════════════════════════════════════════ */

const OR = '#c9a84c', FOND = '#0d0d0d', TEXTE = '#e8e0d0', GRIS = '#8d8676';

const socle = (l, h, corps) => `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:${l}px;height:${h}px;background:${FOND};color:${TEXTE};
       font-family:'DejaVu Serif',Georgia,serif;overflow:hidden;position:relative}
  .cadre{position:absolute;inset:26px;border:1px solid rgba(201,168,76,.30);pointer-events:none}
  .coin{position:absolute;width:22px;height:22px;border:2px solid ${OR};opacity:.75}
  .coin.hg{top:26px;left:26px;border-right:0;border-bottom:0}
  .coin.hd{top:26px;right:26px;border-left:0;border-bottom:0}
  .coin.bg{bottom:26px;left:26px;border-right:0;border-top:0}
  .coin.bd{bottom:26px;right:26px;border-left:0;border-top:0}
  .zone{position:absolute;inset:0;display:flex;flex-direction:column;
        align-items:center;justify-content:center;text-align:center;
        padding:${Math.round(l*0.085)}px ${Math.round(l*0.085)}px ${Math.round(h*0.135)}px}
  .filet{flex:0 0 auto}
  .orn{color:${OR};letter-spacing:.5em;opacity:.55;font-size:${Math.round(l*0.018)}px}
  .filet{width:64px;height:1px;background:${OR};opacity:.5;margin:${Math.round(h*0.035)}px 0}
  .marque{position:absolute;bottom:${Math.round(h*0.052)}px;left:0;right:0;text-align:center;
          color:${GRIS};font-size:${Math.round(l*0.0155)}px;letter-spacing:.16em;text-transform:uppercase}
  em{color:${OR};font-style:italic}
</style></head><body>
  <div class="cadre"></div><div class="coin hg"></div><div class="coin hd"></div>
  <div class="coin bg"></div><div class="coin bd"></div>
  ${corps}
</body></html>`;

export function citation({ texte, source }, l, h) {
  return socle(l, h, `<div class="zone">
    <div class="orn">✦ ✧ ✦</div>
    <div class="filet"></div>
    <div style="font-size:${Math.round(l*0.0425)}px;line-height:1.48;color:${TEXTE};font-style:italic">
      <span style="color:${OR};font-size:1.5em;line-height:0;vertical-align:-.25em">«</span>
      ${texte}
      <span style="color:${OR};font-size:1.5em;line-height:0;vertical-align:-.35em">»</span>
    </div>
    <div class="filet"></div>
    <div style="font-size:${Math.round(l*0.0195)}px;letter-spacing:.11em;color:${OR};text-transform:uppercase">${source}</div>
    <div style="margin-top:${Math.round(h*0.022)}px;font-size:${Math.round(l*0.0175)}px;
                letter-spacing:.05em;color:${GRIS}">Mickaël Darmon</div>
  </div><div class="marque">brith-israel.org</div>`);
}

export function auteur({ lignes, chute, nom }, l, h) {
  const items = lignes.map(t =>
    `<div style="margin:${Math.round(h*0.0135)}px 0;font-size:${Math.round(l*0.0265)}px;line-height:1.4">
       <span style="color:${OR};margin-right:.45em">✦</span>${t}</div>`).join('');
  return socle(l, h, `<div class="zone">
    <div style="font-size:${Math.round(l*0.016)}px;letter-spacing:.22em;color:${OR};text-transform:uppercase">L'auteur</div>
    <div class="filet" style="margin:${Math.round(h*0.028)}px 0"></div>
    <div>${items}</div>
    <div class="filet" style="margin:${Math.round(h*0.028)}px 0"></div>
    <div style="font-size:${Math.round(l*0.0295)}px;font-style:italic;color:${OR};line-height:1.5">${chute}</div>
  </div><div class="marque">${nom} · brith-israel.org</div>`);
}

export function livre({ couverture, titre, sous, meta, lien }, l, h) {
  const paysage = l > h;
  const hCouv = paysage ? Math.round(h * 0.70) : Math.round(h * 0.44);
  return socle(l, h, `<div class="zone" style="${paysage
      ? `flex-direction:row;gap:${Math.round(l*0.055)}px;text-align:left;justify-content:center`
      : ''}">
    <img src="${couverture}" style="height:${hCouv}px;border:1px solid rgba(201,168,76,.35);flex:0 0 auto">
    <div style="${paysage ? 'max-width:52%' : `margin-top:${Math.round(h*0.04)}px`}">
      <div style="font-size:${Math.round(l*0.0395)}px;line-height:1.3;color:${OR}">${titre}</div>
      <div style="margin-top:${Math.round(h*0.022)}px;font-size:${Math.round(l*0.0235)}px;
                  font-style:italic;line-height:1.45">${sous}</div>
      <div style="margin:${Math.round(h*0.03)}px 0;width:56px;height:1px;background:${OR};opacity:.5;
                  ${paysage ? '' : 'margin-left:auto;margin-right:auto'}"></div>
      <div style="font-size:${Math.round(l*0.0185)}px;letter-spacing:.1em;color:${GRIS};text-transform:uppercase">${meta}</div>
      <div style="margin-top:${Math.round(h*0.028)}px;display:inline-block;border:1px solid ${OR};
                  color:${OR};padding:.5em 1.1em;font-size:${Math.round(l*0.0175)}px;letter-spacing:.12em;
                  text-transform:uppercase">${lien}</div>
    </div>
  </div>`);
}

export function reflexion({ texte, nom }, l, h) {
  return socle(l, h, `<div class="zone">
    <div class="orn">\u2726 \u2727 \u2726</div>
    <div class="filet"></div>
    <div style="font-size:${Math.round(l*0.0445)}px;line-height:1.5;color:${TEXTE};font-style:italic">
      <span style="color:${OR};font-size:1.5em;line-height:0;vertical-align:-.25em">\u00ab</span>
      ${texte}
      <span style="color:${OR};font-size:1.5em;line-height:0;vertical-align:-.35em">\u00bb</span>
    </div>
    <div class="filet"></div>
    <div style="font-size:${Math.round(l*0.019)}px;letter-spacing:.14em;color:${GRIS};text-transform:uppercase">${nom}</div>
  </div>`);
}

export const GABARITS = { citation, auteur, livre, reflexion };
