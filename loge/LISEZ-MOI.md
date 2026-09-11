# Gestion des Loges — Rite Brith Israël

Code de l'application de gestion de la R∴L∴ Bereshit n°00.

    Dépôt   contactbrithisrael-tech/nouveausiterbi
    Branche claude/lodge-management-software-19b95p

## Ce que contient ce dossier

### `beta.html` — l'application d'essai
Un seul fichier, sans installation ni serveur. Enregistré sur un
ordinateur et ouvert d'un double-clic, il fonctionne hors ligne : fiches
des membres, carnet et registre des visiteurs, convocation, feuille
d'émargement, planche à tracer modifiable, trésorerie, mode d'emploi.
Les données vivent dans le navigateur de celui qui l'utilise et n'en
sortent jamais. Les documents sortent en Word ou en PDF.

### `schema/` — la base de données
Neuf migrations SQL, à appliquer dans l'ordre de leur numéro. Elles
décrivent 35 tables, écrites d'après la Constitution V9 et le Règlement
Général du Rite, non d'après l'usage maçonnique courant.

    001_socle.sql            loges, membres, affiliations, degrés, offices
    002_acces.sql            comptes, sessions, jetons, journal d'accès
    003_tenues.sql           tenues, ordre du jour, travaux, présences, visiteurs
    004_envois.sql           invitations, campagnes, envois nominatifs
    005_tronc_amities.sql    Tronc de la Veuve, obédiences et loges amies
    006_planches.sql         planches à tracer, paragraphes, signatures
    007_tresorerie.sql       exercices, barème, appels, règlements, caisse
    008_echeances.sql        échéanciers, droits d'initiation et d'affiliation
    009_excuse_permanent.sql membres excusés d'office

Pour la monter d'un coup, sur n'importe quel SQLite :

    cat schema/0*.sql | sqlite3 loge.db

### `lib/formules.js` — les règles d'écriture du Rite
L'An de Vraie Lumière (année vulgaire + 3760, d'après la Constitution),
la pierre plate du Tronc (le kilogramme vaut l'euro, le gramme le
centime), le mois maçonnique, les ordinaux, l'élision du degré. Chaque
règle cite sa source ; celle dont la source manque le dit en clair.

### `gabarits/planche-a-tracer.html` — le modèle imprimable
Format A4. La forme de votre modèle, reprise mot pour mot, purgée de ce
qui venait du Rite Écossais. Ce qui est entre `{{ }}` est calculé.

### `assets/` — les images
Sceau du Suprême Conseil, sceau de Bereshit, filigrane.

## Ce qui n'existe pas encore

Il n'y a pas de serveur. Rien n'est déployé, aucun courriel ne part tout
seul, aucune donnée n'est partagée entre deux ordinateurs. Le déploiement
prévu — Cloudflare Pages, base D1, archives R2, envoi par Brevo — attend
les accès du compte.
