/* ═══════════════════════════════════════════════════════════════
   RITE BRITH ISRAËL — images.js
   
   Injecte les photos et PDFs base64 dans la page.
   Chargé en dernier → n'affecte pas les performances.
   
   Pour remplir ce fichier automatiquement :
   → lance : python3 patch_extract_images.py
════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ─────────────────────────────────────────────
     IMAGES — remplacer "" par les base64 réelles
     Format : "data:image/jpeg;base64,/9j/4AAQ..."
  ───────────────────────────────────────────── */
  var IMG = {
    // Sceau principal (hero + navbar)
    SCEAU_RBI:          "",

    // Photos membres (Chefs de l'Ordre)
    PHOTO_DARMON:       "",
    PHOTO_RAUX:         "",
    PHOTO_HABERT:       "",
    PHOTO_CARILLO:      "",
    PHOTO_BUHLER:       "",
    PHOTO_NOTARIANNI:   "",
    PHOTO_JOURDAN:      "",

    // Couvertures livres
    BOOK_ALLIANCE:      "",
    BOOK_GUIDE:         "",

    // PDFs tuilage (data:application/pdf;base64,...)
    PDF_1: "",
    PDF_2: "",
    PDF_3: ""
  };

  /* ─────────────────────────────────────────────
     INJECTION
  ───────────────────────────────────────────── */
  function setImg(id, src) {
    if (!src) return;
    var el = document.getElementById(id);
    if (el) { el.src = src; }
  }

  function setPDF(btnId, src, label) {
    if (!src) return;
    var btn = document.getElementById(btnId);
    if (!btn) return;
    btn.href     = src;
    btn.download = (label || 'document') + '.pdf';
    btn.style.display = '';
  }

  document.addEventListener('DOMContentLoaded', function () {

    /* Sceau */
    setImg('nav-logo',  IMG.SCEAU_RBI);
    setImg('hero-seal', IMG.SCEAU_RBI);

    /* Photos Chefs de l'Ordre */
    setImg('photo-darmon',     IMG.PHOTO_DARMON);
    setImg('photo-raux',       IMG.PHOTO_RAUX);
    setImg('photo-habert',     IMG.PHOTO_HABERT);
    setImg('photo-carillo',    IMG.PHOTO_CARILLO);
    setImg('photo-buhler',     IMG.PHOTO_BUHLER);
    setImg('photo-notarianni', IMG.PHOTO_NOTARIANNI);
    setImg('photo-jourdan',    IMG.PHOTO_JOURDAN);

    /* Livres */
    setImg('book-alliance', IMG.BOOK_ALLIANCE);
    setImg('book-guide',    IMG.BOOK_GUIDE);

    /* PDFs tuilage */
    var cfgPdfs = window.RBI_CONFIG && window.RBI_CONFIG.tuilage && window.RBI_CONFIG.tuilage.pdfs;
    if (cfgPdfs) {
      setPDF(cfgPdfs[0].id, IMG.PDF_1, cfgPdfs[0].label);
      setPDF(cfgPdfs[1].id, IMG.PDF_2, cfgPdfs[1].label);
      setPDF(cfgPdfs[2].id, IMG.PDF_3, cfgPdfs[2].label);
    }

  });

})();


/* ════════════════════════════════════════════════════════════════
   SCRIPT D'EXTRACTION AUTOMATIQUE
   Fichier : patch_extract_images.py
   Usage   : python3 patch_extract_images.py
   
   Place ce fichier dans le même dossier que alliance.html.
   Il lit alliance.html et remplit automatiquement images.js.
═══════════════════════════════════════════════════════════════ */
/*

#!/usr/bin/env python3
import re, os, sys

SRC  = 'alliance.html'
DEST = 'assets/images.js'

if not os.path.exists(SRC):
    print(f"[RBI] ERREUR : {SRC} introuvable."); sys.exit(1)

print(f"[RBI] Lecture de {SRC} ({os.path.getsize(SRC)//1024} Ko)...")
with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

def find_by_id(html, eid):
    # Cherche src="..." sur une balise avec id="eid"
    patterns = [
        rf'id=["\'{eid}["\'][^>]*src=["\']([^"\']+)["\']',
        rf'src=["\']([^"\']+)["\'][^>]*id=["\'{eid}["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.DOTALL)
        if m and m.group(1).startswith('data:'): return m.group(1)
    return ''

def find_first_img(html):
    m = re.search(r'src=["\']([^"\']*data:image[^"\']+)["\']', html)
    return m.group(1) if m else ''

def find_pdfs(html):
    return re.findall(
        r'href=["\']([^"\']*data:application/pdf[^"\']+)["\']',
        html
    )

# Extraction
ids = {
    'SCEAU_RBI':        find_by_id(html, 'hero-seal') or find_first_img(html),
    'PHOTO_DARMON':     find_by_id(html, 'photo-darmon'),
    'PHOTO_RAUX':       find_by_id(html, 'photo-raux'),
    'PHOTO_HABERT':     find_by_id(html, 'photo-habert'),
    'PHOTO_CARILLO':    find_by_id(html, 'photo-carillo'),
    'PHOTO_BUHLER':     find_by_id(html, 'photo-buhler'),
    'PHOTO_NOTARIANNI': find_by_id(html, 'photo-notarianni'),
    'PHOTO_JOURDAN':    find_by_id(html, 'photo-jourdan'),
    'BOOK_ALLIANCE':    find_by_id(html, 'book-alliance'),
    'BOOK_GUIDE':       find_by_id(html, 'book-guide'),
}

pdfs = find_pdfs(html)
ids['PDF_1'] = pdfs[0] if len(pdfs) > 0 else ''
ids['PDF_2'] = pdfs[1] if len(pdfs) > 1 else ''
ids['PDF_3'] = pdfs[2] if len(pdfs) > 2 else ''

for k, v in ids.items():
    status = f"{len(v)//1024} Ko" if v else "VIDE"
    print(f"[RBI] {k:20s} : {status}")

# Lecture et mise à jour de images.js
with open(DEST, 'r', encoding='utf-8') as f:
    js = f.read()

for key, val in ids.items():
    js = re.sub(
        rf'({re.escape(key)}\s*:\s*)"[^"]*"',
        rf'\1"{val}"',
        js
    )

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(js)

print(f"\n[RBI] ✓ {DEST} mis à jour avec succès.")
print("[RBI] → Upload assets/images.js sur GitHub.")

*/
