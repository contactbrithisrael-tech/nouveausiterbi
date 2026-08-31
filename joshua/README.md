# Joshua

Assistant IA conversationnel accessible par Telegram, capable de répondre à
partir d'une base documentaire de plusieurs millions de passages sans jamais
envoyer cette base au modèle.

**Claude** raisonne et formule · **Qdrant** est la mémoire documentaire ·
**PostgreSQL** tient les utilisateurs, conversations et le catalogue ·
**Redis** sert de cache · **Telegram** est l'interface.

---

## Table des matières

1. [Créer le bot avec BotFather](#1-créer-le-bot-avec-botfather)
2. [Récupérer TELEGRAM_BOT_TOKEN](#2-récupérer-telegram_bot_token)
3. [Créer la clé Anthropic](#3-créer-la-clé-anthropic)
4. [Configurer le .env](#4-configurer-le-env)
5. [Docker Compose](#5-docker-compose)
6. [Lancer Joshua](#6-lancer-joshua)
7. [Importer des documents](#7-importer-des-documents)
8. [Tester depuis Telegram](#8-tester-depuis-telegram)
9. [Sauvegarder Qdrant et PostgreSQL](#9-sauvegarder-qdrant-et-postgresql)
10. [Mettre à jour](#10-mettre-à-jour)

Puis : [architecture](#architecture), [décisions techniques](#décisions-techniques-et-corrections-apportées),
[bibliothèque iCloud](#bibliothèque-icloud), [dépannage](#dépannage).

---

## 1. Créer le bot avec BotFather

1. Ouvrir Telegram et démarrer une conversation avec **@BotFather**.
2. Envoyer `/newbot`.
3. Choisir un nom affiché (« Joshua ») puis un identifiant unique se
   terminant par `bot` (« joshua_rbi_bot »).
4. BotFather répond avec le jeton.

Réglages utiles, toujours via BotFather :

```
/setdescription   texte affiché avant le premier message
/setabouttext     texte de la fiche du bot
/setcommands      liste des commandes proposées à la saisie
```

Pour `/setcommands`, coller :

```
start - Présentation de Joshua
help - Aide et commandes
status - État des services
mode - Niveau d'accès actuel
logout - Revenir au mode public
```

Les commandes d'administration ne sont **volontairement pas** déclarées ici :
inutile d'annoncer `/stats` et `/reindex` à tous les utilisateurs.

## 2. Récupérer TELEGRAM_BOT_TOKEN

Le jeton ressemble à `123456789:AAEhBOweik6ad9r_AbCdEfGhIjKlMnOpQrStUv`.

Il donne le contrôle total du bot : il ne doit figurer que dans le `.env`,
jamais dans le dépôt. En cas de fuite, `/revoke` auprès de BotFather.

Récupérer aussi **votre** identifiant Telegram numérique pour les commandes
d'administration : démarrer une conversation avec **@userinfobot**, qui répond
un nombre. C'est la valeur de `ADMIN_TELEGRAM_IDS`.

## 3. Créer la clé Anthropic

1. Se connecter sur <https://console.anthropic.com>.
2. **API Keys** → **Create Key**.
3. Copier la valeur `sk-ant-…` : elle n'est affichée qu'une fois.
4. Vérifier qu'un moyen de paiement est enregistré (**Billing**), sans quoi
   les appels échouent avec une erreur de crédit.

Le nom du modèle se règle par `ANTHROPIC_MODEL` et **n'apparaît nulle part
ailleurs dans le code** : en changer est une modification du `.env`.

## 4. Configurer le .env

```bash
cp .env.example .env
```

Puis renseigner au minimum :

| Variable | Rôle | Obligatoire |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | jeton BotFather | oui |
| `ANTHROPIC_API_KEY` | clé Anthropic | oui |
| `POSTGRES_PASSWORD` | mot de passe de la base | oui |
| `ADMIN_TELEGRAM_IDS` | identifiants admin, séparés par des virgules | recommandé |
| `JOSHUA_LIBRARY_PATH` | dossier de la bibliothèque (iCloud ou autre) | pour l'indexation |
| `ANTHROPIC_MODEL` | modèle utilisé | valeur par défaut fournie |

`docker compose` **refuse de démarrer** si `POSTGRES_PASSWORD` est vide : une
base de production sans mot de passe est une erreur qu'il vaut mieux voir
immédiatement.

## 5. Docker Compose

Quatre services :

| Service | Rôle | Volume persistant |
|---|---|---|
| `joshua` | bot + API | `models_cache` (modèle d'embeddings) |
| `postgres` | utilisateurs, conversations, catalogue | `postgres_data` |
| `qdrant` | index vectoriel | `qdrant_storage` |
| `redis` | cache et limitation de débit | `redis_data` |

`joshua` attend que les trois autres soient **sains**, pas seulement
démarrés : un PostgreSQL « démarré » refuse encore les connexions pendant
plusieurs secondes.

Le port PostgreSQL n'est pas exposé à l'hôte (à décommenter pour inspecter la
base en développement). Qdrant expose 6333 pour son tableau de bord :
<http://localhost:6333/dashboard>.

## 6. Lancer Joshua

```bash
docker compose up -d          # construit et démarre tout
docker compose logs -f joshua # suivre le démarrage
curl localhost:8000/health    # état réel des dépendances
```

Créer le schéma de base à la première installation :

```bash
docker compose exec joshua alembic upgrade head
```

En développement, sans Docker pour l'application :

```bash
make install                              # venv + dépendances + .env
docker compose up -d postgres qdrant redis
make migrate
make dev
```

Le premier démarrage télécharge le modèle d'embeddings (~1 Go) : comptez
quelques minutes, une seule fois — le volume `models_cache` le conserve.

## 7. Importer des documents

Deux chemins, selon l'origine des documents.

### Dossier de dépôt

```bash
cp mes_documents/*.pdf data/incoming/
python scripts/ingest.py data/incoming/
python scripts/ingest.py data/incoming/ --category reglements --tags interne,2026
```

Formats pris en charge : **PDF, EPUB, DOCX, TXT, Markdown, CSV, JSON/JSONL**.

### Corpus RBI (documents officiels du Rite)

```bash
python scripts/import_rbi.py --dry-run   # que va-t-il être importé ?
python scripts/import_rbi.py             # importe le corpus
python scripts/import_rbi.py --library   # + la bibliothèque personnelle
```

Le script cherche les documents dans cet ordre : `--source`, puis
`JOSHUA_RBI_SOURCE`, puis `data/incoming/rbi/`, puis la racine du dépôt du
site — où les PDF publiés se trouvent déjà. **Les originaux ne sont ni
copiés, ni déplacés, ni modifiés.**

Sur le repli « racine du dépôt », le parcours est volontairement **à plat et
restreint aux formats documentaires** (`.pdf`, `.epub`, `.docx`) : un dépôt
contient des `.json` et des `.md` qui sont du code et de la configuration,
pas des documents. Un dossier désigné explicitement, lui, n'est pas restreint.

Les documents importés portent `category=rbi`, `source=rbi_officiel` et les
étiquettes `rbi, officiel` — ce sont ces valeurs qui permettent de filtrer
une recherche sur le seul corpus de l'Ordre.

#### Vos livres sont dans un dossier du Mac

Exemple : `/Users/Mickael Darmon/Desktop/livres rbi`.

**1. Déclarer le dossier une seule fois**

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

Le fichier contient déjà le montage :

```yaml
services:
  joshua:
    volumes:
      - "/Users/Mickael Darmon/Desktop/livres rbi:/library:ro"
    environment:
      JOSHUA_RBI_SOURCE: /library
```

`:ro` = lecture seule : le noyau refuse toute écriture, quoi que fasse le
programme. Les guillemets sont obligatoires, le chemin contenant des espaces.

**2. Importer**

```bash
docker compose up -d
docker compose exec joshua python scripts/import_rbi.py --dry-run
docker compose exec joshua python scripts/import_rbi.py
```

L'import s'exécute **dans le conteneur**, où le dossier est visible sous
`/library`. Le chemin macOS n'existe pas là où le code tourne : c'est
`JOSHUA_RBI_SOURCE=/library` que les scripts lisent.

**Deux autorisations macOS à vérifier**, sans quoi le montage apparaît vide
sans le moindre message d'erreur :

| Réglage | Où |
|---|---|
| Partage de fichiers | Docker Desktop → Settings → Resources → File sharing (le dossier ou `/Users`) |
| Accès complet au disque | Réglages Système → Confidentialité et sécurité (cocher Docker Desktop) |

Le Bureau est souvent synchronisé par iCloud (« Dossiers Bureau et
Documents »). Les livres restés dans le nuage sont détectés, signalés
`icloud_not_downloaded`, et n'interrompent rien. Pour les rapatrier : ouvrir
le dossier dans le Finder, attendre la fin des téléchargements, relancer
l'import — seuls les nouveaux seront traités.

Ce que Joshua fait de ce dossier, vérifié sur une arborescence réelle
(sous-dossiers, accents, espaces, `.DS_Store`, livre évincé par iCloud) :

```
livres rbi/
├── Constitution du Rite.pdf          → 16 chunks, pages 1 à 35
├── notes perso.txt                   →  1 chunk
├── .DS_Store                         →  ignoré
├── couverture.jpg                    →  ignoré (format non documentaire)
├── Rituels/
│   ├── Rituel 1er degré.pdf          →  1 chunk
│   └── .Rituel 3e degré.epub.icloud  →  icloud_not_downloaded (signalé, non bloquant)
└── Traités/
    └── Traité d'amitié.pdf           →  1 chunk

5 fichiers vus · 4 indexés · 1 dans le nuage · 0 erreur · 19 chunks
```

### Bibliothèque existante (iCloud, NAS, disque externe)

```bash
python scripts/index_library.py --scan     # inventaire, n'indexe rien
python scripts/index_library.py --update   # nouveautés et modifications
python scripts/index_library.py --full     # reconstruction complète
```

Dans les deux cas :

* les fichiers déjà indexés et inchangés sont ignorés (empreinte SHA-256) ;
* un document illisible est journalisé, l'import continue ;
* la progression s'affiche sur `stderr`, le rapport final en JSON sur
  `stdout` — donc `python scripts/ingest.py data/incoming/ > rapport.json`
  produit un fichier exploitable.

## 8. Tester depuis Telegram

1. Ouvrir la conversation avec votre bot.
2. `/start` — présentation.
3. `/status` — doit indiquer la base documentaire disponible et le nombre de
   passages indexés.
4. Poser une question portant sur un document importé.

Une réponse correcte cite ses sources :

```
Selon les documents disponibles, la procédure prévoit trois étapes [1],
et le délai applicable est de trente jours [2].

Sources :
[1] Manuel_X.pdf — page 47
[2] Reglement.pdf — 3.2
```

Commandes d'administration (réservées à `ADMIN_TELEGRAM_IDS`) :
`/stats`, `/sources`, `/reindex`. Pour un non-administrateur, elles répondent
« Commande inconnue » — leur existence n'est pas divulguée.

### Modes d'accès

| Commande | Effet |
|---|---|
| `/mode` | affiche le niveau d'accès réellement enregistré |
| `/ff <mot de passe>` | passe en mode Frère/Sœur |
| `/sgc <mot de passe>` | passe en mode Souverain Grand Commandeur |
| `/logout` | revient au mode public |

```
🟢 Mode actuel : Public (profane)
🟡 Mode actuel : Frère/Sœur
🔴 Mode actuel : SGC
```

Le mode est **persisté dans PostgreSQL**, attaché au `telegram_user_id`. Il
survit donc à un redémarrage du bot et reste correct avec plusieurs instances
— contrairement à `context.user_data`, qui est la cause habituelle du
symptôme « le mot de passe est accepté mais `/mode` affiche encore public ».

Traitement du secret, à chaque étape :

* la comparaison est faite **par le code**, avec `hmac.compare_digest` : le
  modèle de langage n'est jamais consulté et ne voit ni le mot de passe, ni
  la tentative ;
* un secret non configuré n'authentifie **jamais** ;
* le message contenant le mot de passe est effacé du salon ;
* il n'est ni journalisé, ni enregistré en base (les commandes échappent au
  gestionnaire qui écrit l'historique), ni renvoyé dans une réponse ;
* cinq échecs par quart d'heure et par utilisateur, puis refus temporaire.

Effet sur les réponses : le mode restreint la recherche documentaire **par
exclusion** (`must_not access_level`). Un document indexé sans niveau déclaré
reste visible de tous — un filtre par inclusion aurait masqué d'un coup tout
le corpus existant, panne totale déguisée en sécurité. Le marquage des
documents réservés se fera à l'ingestion.

## 9. Sauvegarder Qdrant et PostgreSQL

**PostgreSQL** — sauvegarde logique, la plus simple à restaurer :

```bash
docker compose exec -T postgres pg_dump -U joshua joshua | gzip > joshua_$(date +%F).sql.gz
# restauration
gunzip -c joshua_2026-01-15.sql.gz | docker compose exec -T postgres psql -U joshua -d joshua
```

**Qdrant** — instantané natif, cohérent même pendant les écritures :

```bash
curl -X POST http://localhost:6333/collections/joshua_documents/snapshots
docker compose cp qdrant:/qdrant/storage/snapshots ./sauvegardes/
```

**Que sauvegarder en priorité ?** PostgreSQL. L'index Qdrant est
*reconstructible* à partir des documents sources et du catalogue
(`index_library.py --full`), alors que les conversations, elles, sont
irremplaçables. Sauvegarder Qdrant fait gagner des heures de réindexation,
pas des données.

## 10. Mettre à jour

```bash
git pull
docker compose build joshua
docker compose up -d joshua
docker compose exec joshua alembic upgrade head   # si le schéma a changé
```

**Changement du modèle d'embeddings** — cas particulier, à traiter comme une
migration de données :

```bash
python scripts/reindex.py --full        # supprime la collection (confirmation demandée)
python scripts/index_library.py --full  # reconstruit l'index
```

Les vecteurs de deux modèles différents ne sont pas comparables. Sauter cette
étape ne provoque **aucune erreur** : Joshua répondrait simplement à côté, ce
qui est le pire des symptômes.

---

## Architecture

```
Telegram
   │  « Que dit le règlement sur X ? »
   ▼
handlers.py ── limitation de débit ── nettoyage de l'entrée
   │
   ├──► PostgreSQL : utilisateur, conversation, message, historique récent + résumé
   │
   ├──► RAG ─── embedding de la question (cache Redis)
   │             │
   │             ▼
   │          Qdrant : 30 candidats ─► MMR + plafond par document ─► 10 passages
   │             │
   │             ▼
   │          contexte balisé <documents> + table des sources
   │
   ├──► Claude : prompt système + historique + contexte + question
   │
   ├──► vérification des citations (aucune référence inventée)
   │
   ▼
Telegram (réponse découpée en messages de 4096 caractères)
```

Ingestion :

```
PDF / EPUB / DOCX / TXT / MD / CSV / JSON
        │  loader.py     (parcours, détection iCloud)
        │  deduplication (SHA-256 : fichier déjà vu ?)
        │  parser.py     (extraction, page/section conservées)
        │  chunker.py    (~1000 tokens, recouvrement 120, phrases entières)
        │  embeddings    (FastEmbed local, par lots)
        ▼
     Qdrant (upsert par lots)  +  PostgreSQL (une ligne par document)
```

### Répartition des responsabilités

| Composant | Détient | Ne détient pas |
|---|---|---|
| Qdrant | vecteurs, texte des chunks, métadonnées de citation | conversations |
| PostgreSQL | utilisateurs, messages, catalogue, jobs | texte des chunks |
| Redis | cache d'embeddings, compteurs de débit | rien de durable |
| Claude | raisonnement, formulation | aucune donnée persistée |

Le texte des chunks n'existe **qu'à un seul endroit** (Qdrant). Le dupliquer
en base doublerait le volume pour une donnée déjà renvoyée avec chaque
résultat de recherche.

---

## Décisions techniques et corrections apportées

Le cahier des charges laissait plusieurs points ouverts. Voici les choix
retenus, et pourquoi.

### 1. Comptage des tokens à l'ingestion

Anthropic ne publie pas de tokenizer local, et compter exactement imposerait
un appel réseau **par chunk** — inenvisageable sur des millions de chunks. Le
découpage travaille donc en caractères, via un ratio configurable
(`CHARS_PER_TOKEN=3.6`, mesuré sur du français accentué ; l'anglais est plus
proche de 4.0). L'erreur est d'environ 10 %, absorbée par la marge de la
fenêtre de contexte.

### 2. `ADMIN_TELEGRAM_IDS` déclaré en chaîne, pas en liste

pydantic-settings tente de décoder en JSON toute variable typée `list`.
`ADMIN_TELEGRAM_IDS=123,456` échouerait au démarrage avec une erreur de
parsing incompréhensible. Le champ est donc une chaîne, et `admin_ids` en
dérive un ensemble d'entiers — une entrée invalide est ignorée plutôt que de
mettre le bot hors service.

### 3. Deux pilotes PostgreSQL

`asyncpg` pour le bot (des requêtes courtes et concurrentes), `psycopg` pour
l'ingestion et Alembic (un long traitement séquentiel). Imposer l'asynchrone
à l'ingestion n'apporterait aucun parallélisme réel, seulement de la
complexité.

### 4. Deux tailles distinctes dans le RAG

`RAG_CANDIDATES=30` est ce qu'on demande à Qdrant, `RAG_FINAL_CHUNKS=10` ce
qu'on envoie à Claude. Chercher large coûte quelques millisecondes et améliore
nettement le rappel ; envoyer large coûte des jetons **à chaque message** et
dilue le signal.

### 5. Diversification MMR et plafond par document

Sans diversification, les dix meilleurs résultats sont souvent dix
formulations du même passage. Le MMR arbitre entre pertinence et redondance,
et `max_par_document=4` empêche un ouvrage volumineux de monopoliser le
contexte. La redondance est mesurée sur le texte (Jaccard) et non sur les
vecteurs : ceux-ci ne sont volontairement pas rapatriés depuis Qdrant, ils
pèsent 4 Ko par point pour un usage nul dans la génération.

### 6. Réponses envoyées en texte brut

Telegram rejette un message **entier** dont le Markdown est mal formé — et un
texte produit par un modèle contient régulièrement un astérisque isolé ou un
souligné dans un nom de fichier. Le rendu est un confort, la livraison est la
fonction. Le découpage préserve en revanche les blocs de code : un ``` non
refermé casserait l'affichage de toute la suite de la conversation.

### 7. Défense en profondeur contre l'injection par les documents

Le vecteur d'attaque le moins intuitif : quiconque peut déposer un PDF dans la
bibliothèque peut y écrire « ignore tes instructions ». Trois couches
indépendantes :

1. le prompt système déclare explicitement le contenu documentaire non fiable
   **au niveau des instructions** ;
2. les extraits sont encadrés par `<documents>`, avec un rappel de la règle
   **après** le contenu (un modèle accorde plus de poids à ce qui est proche
   de la fin) ;
3. les séquences imitant une balise ou une frontière de rôle sont désamorcées
   (`</documents>` → `⟦/documents⟧`) — désamorcées et non supprimées, pour ne
   pas mutiler un contenu légitime.

Aucune couche n'est suffisante seule.

### 8. Vérification des citations

Les numéros `[n]` produits par Claude sont confrontés à la table des sources
réellement fournies. Une référence inventée est journalisée et n'est jamais
affichée à l'utilisateur.

### 9. Identifiants de chunks déterministes

`chunk_id = uuid5(document_id, index)`. Réindexer un document réécrit les
mêmes points au lieu d'en créer de nouveaux : l'opération devient idempotente
même si la suppression préalable a échoué.

### 10. Déduplication à deux niveaux

Fichier (SHA-256 du binaire) pour « ce livre est-il déjà indexé ? », chunk
(SHA-256 du texte normalisé) pour « ce passage existe-t-il déjà ? ». Sur une
bibliothèque réelle, les mêmes préfaces et mentions légales reviennent des
centaines de fois.

### 11. Pas d'OCR par défaut

Un PDF scanné sans couche texte est signalé, pas traité. Ajouter Tesseract
représente plusieurs secondes par page et une dépendance système ; c'est une
décision d'infrastructure qui n'a pas sa place dans le chemin d'ingestion par
défaut. Branchement possible dans `app/parsers/pdf.py`, à l'endroit où les
pages vides sont comptées.

### 12. `/reindex` n'indexe pas depuis le bot

Une ingestion dure des heures. La lancer dans le processus qui répond aux
utilisateurs le rendrait indisponible. La commande affiche l'état et rappelle
l'invocation à exécuter côté serveur.

### 13. Inventaire et import parcourent le même ensemble

`ingerer()` accepte `extensions` et `profondeur_max`, et `import_rbi.py`
passe les **mêmes** règles à son inventaire (`--dry-run`) et à son import.
Deux chemins de code qui « filtrent pareil » finissent toujours par filtrer
différemment : lors de la vérification, l'aperçu annonçait 3 documents et
l'ingestion réelle en avalait 18, dont `package.json` et `structure.txt`.

### 14. Polling par défaut, webhook sans réécriture

`construire_application()` renvoie la même `Application` dans les deux cas ;
seule la réception change. Passer en webhook, c'est régler `TELEGRAM_MODE`,
`TELEGRAM_WEBHOOK_URL` et `TELEGRAM_WEBHOOK_SECRET` — aucun gestionnaire n'est
modifié. La route webhook vérifie le jeton secret et traite la mise à jour en
tâche de fond : Telegram réémet toute mise à jour non acquittée en quelques
secondes, et une réponse de vingt secondes produirait des doublons.

### 15. Dégradation plutôt qu'arrêt

Redis absent : le cache et la limitation basculent en mémoire locale. Qdrant
absent : Joshua converse sans documents et le dit. PostgreSQL absent : `/health`
passe en `degraded`. Seules les variables réellement indispensables
(`TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`) empêchent le démarrage.

---

## Bibliothèque iCloud

`JOSHUA_LIBRARY_PATH` désigne la bibliothèque **source**, Qdrant en est
l'**index**. Exemple macOS :

```
JOSHUA_LIBRARY_PATH="/Users/moi/Library/Mobile Documents/com~apple~CloudDocs/Joshua"
```

Garanties, techniques et pas seulement déclaratives :

* aucun fichier n'est écrit, renommé, déplacé ou supprimé dans la
  bibliothèque — le code n'ouvre qu'en lecture, et le montage Docker
  recommandé est `:ro` ;
* les fichiers présents dans le Finder mais **non téléchargés** sont détectés
  (fantômes `.Nom.pdf.icloud`), signalés `icloud_not_downloaded`, et n'arrêtent
  rien ;
* aucun rapatriement n'est déclenché : forcer le téléchargement de centaines
  de gigaoctets est une décision qui appartient à l'utilisateur.

Cycle habituel :

```bash
python scripts/index_library.py --scan     # que va-t-il se passer ?
python scripts/index_library.py --update   # indexe nouveautés et modifications
```

`--scan` répond avant tout import massif :

```json
{
  "total": 4821,
  "par_type": {"pdf": 3910, "epub": 802, "docx": 109},
  "deja_indexes": 4700,
  "nouveaux": 98,
  "modifies": 3,
  "indisponibles_localement": 20,
  "volume_go": 61.4
}
```

Pour retirer de l'index les livres supprimés de la bibliothèque, ajouter
`--purge-absents`. La purge n'a lieu **que** si la racine a bien été
parcourue : un volume iCloud non monté ne peut pas vider l'index.

---

## Tests

```bash
make test          # ou : python -m pytest tests/ -v
```

119 tests, aucune infrastructure requise : ni PostgreSQL, ni Qdrant, ni Redis,
ni clé Anthropic, ni modèle d'embeddings. Une suite qui exige une
infrastructure n'est pas exécutée, donc ne protège de rien.

| Fichier | Couvre |
|---|---|
| `test_chunking.py` | tailles, recouvrement, abréviations, métadonnées |
| `test_deduplication.py` | empreintes fichier et chunk, scans incrémentaux |
| `test_rag.py` | recherche, seuil, MMR, budget de contexte, citations |
| `test_permissions.py` | admins, limitation de débit, repli sans Redis |
| `test_telegram_split.py` | découpage 4096, blocs de code, intégrité |
| `test_securite.py` | injection par documents, masquage des secrets |
| `test_memoire.py` | alternance des rôles, injection du résumé |
| `test_ingestion.py` | iCloud, dispatch, lots, isolation des erreurs |
| `test_import_rbi.py` | sélection des sources, règles de scan partagées |
| `test_auth_modes.py` | modes d'accès : validation, persistance, isolation, enregistrement des commandes |
| `test_integration_qdrant.py` | ingestion → recherche de bout en bout (Qdrant local) |

Le test d'intégration utilise le moteur Qdrant **embarqué** du client
officiel : même code de recherche, stockage temporaire, aucune infrastructure.
C'est lui qui a révélé un appel incompatible entre le pipeline et la couche
Qdrant que les tests unitaires, chacun correct de son côté, ne pouvaient pas
voir.

---

## Dépannage

| Symptôme | Cause probable | Action |
|---|---|---|
| Le bot ne répond pas | jeton invalide, ou deux instances en polling | `docker compose logs joshua` ; une seule instance à la fois |
| « Joshua rencontre momentanément un problème » | erreur côté serveur | les journaux portent la cause exacte et le `request_id` |
| Réponses sans source | index vide ou seuil trop haut | `/status`, puis baisser `RAG_MIN_SCORE` |
| `/stats` signale un écart PostgreSQL/Qdrant | index désynchronisé | `scripts/reindex.py --full` puis réindexation |
| Démarrage très lent la première fois | téléchargement du modèle (~1 Go) | normal, une seule fois (volume `models_cache`) |
| `POSTGRES_PASSWORD est obligatoire` | variable vide | la renseigner dans `.env` |
| Beaucoup de `icloud_not_downloaded` | fichiers non rapatriés | ouvrir le dossier dans le Finder, forcer le téléchargement, relancer `--update` |
| `aucun document RBI trouvé` alors que le dossier existe | montage Docker vide | vérifier File sharing et l'Accès complet au disque (voir plus haut), puis `docker compose exec joshua ls -la /library` |
| Les livres sont importés deux fois | `JOSHUA_RBI_SOURCE` et `JOSHUA_LIBRARY_PATH` sur le même dossier | n'en garder qu'un : deux catégories exigent deux dossiers distincts |

Les journaux sont structurés en JSON et portent `request_id`, `telegram_user_id`,
`module` et `duration_ms` :

```bash
docker compose logs joshua | jq 'select(.level=="error")'
docker compose logs joshua | jq 'select(.event=="message_traite") | .duration_ms'
```
