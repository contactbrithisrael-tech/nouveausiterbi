"""Configuration centrale de Joshua.

Choix d'architecture
--------------------
1. **Une seule source de vérité.** Tous les réglages transitent par cet
   objet ``Settings``. Aucun ``os.getenv`` n'est autorisé ailleurs dans le
   code : un paramètre lu à deux endroits finit toujours par diverger, et le
   nom du modèle Anthropic en est l'exemple canonique (le cahier des charges
   l'exige explicitement).

2. **Champs « listes » déclarés en ``str``.** pydantic-settings tente de
   décoder en JSON toute variable d'environnement dont le champ est typé
   ``list``/``set``. ``ADMIN_TELEGRAM_IDS=123,456`` échouerait donc au
   démarrage avec une erreur de parsing JSON peu compréhensible. On lit
   la valeur brute et on expose une propriété dérivée : c'est le seul
   moyen fiable de garder la syntaxe « séparé par des virgules » demandée.

3. **Aucune valeur par défaut pour les secrets.** ``TELEGRAM_BOT_TOKEN`` et
   ``ANTHROPIC_API_KEY`` n'ont pas de valeur : l'application refuse de
   démarrer si elles manquent, plutôt que de tourner dans un état à moitié
   fonctionnel qui échouerait au premier message reçu.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Les variables inconnues sont ignorées : le .env d'un poste de
        # développement contient souvent des clés propres à l'utilisateur
        # (proxy, éditeur) qui ne doivent pas faire échouer le démarrage.
        extra="ignore",
    )

    # ── Telegram ────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str
    # Le mode est un réglage, pas une réécriture : la couche bot expose la
    # même Application dans les deux cas (voir app/bot/telegram.py).
    TELEGRAM_MODE: Literal["polling", "webhook"] = "polling"
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_MAX_MESSAGE_CHARS: int = 4096

    # ── Anthropic ───────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    ANTHROPIC_MAX_TOKENS: int = 2048
    ANTHROPIC_TEMPERATURE: float = 0.2
    ANTHROPIC_TIMEOUT_SECONDS: float = 120.0
    ANTHROPIC_MAX_RETRIES: int = 3

    # ── Qdrant ──────────────────────────────────────────────────────
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "joshua_documents"
    QDRANT_BATCH_SIZE: int = 256
    # HNSW : valeurs pensées pour plusieurs millions de points. m=32 double
    # la mémoire de l'index par rapport au défaut (16) mais préserve le
    # rappel quand la base grossit — arbitrage assumé, documenté au README.
    QDRANT_HNSW_M: int = 32
    QDRANT_HNSW_EF_CONSTRUCT: int = 256

    # ── PostgreSQL ──────────────────────────────────────────────────
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "joshua"
    POSTGRES_USER: str = "joshua"
    POSTGRES_PASSWORD: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ── Redis ───────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    RATE_LIMIT_MESSAGES: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Embeddings ──────────────────────────────────────────────────
    EMBEDDING_PROVIDER: Literal["fastembed", "voyage", "openai"] = "fastembed"
    # Modèle multilingue : la bibliothèque contient du français, et un modèle
    # anglais seul dégraderait fortement le rappel sur ce corpus.
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_BATCH_SIZE: int = 64
    EMBEDDING_CACHE_TTL_SECONDS: int = 86400
    VOYAGE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── RAG ─────────────────────────────────────────────────────────
    RAG_CANDIDATES: int = 30
    RAG_FINAL_CHUNKS: int = 10
    RAG_MIN_SCORE: float = 0.30
    # Diversification MMR : évite que les 10 passages retenus proviennent
    # tous de la même page d'un même livre.
    RAG_MMR_LAMBDA: float = 0.7
    RAG_MAX_CONTEXT_CHARS: int = 24000

    # ── Chunking ────────────────────────────────────────────────────
    CHUNK_TARGET_TOKENS: int = 1000
    CHUNK_OVERLAP_TOKENS: int = 120
    CHUNK_MIN_TOKENS: int = 80
    # Approximation tokens↔caractères. Anthropic ne publie plus de
    # tokenizer local ; compter les tokens exactement exigerait un appel
    # réseau par chunk, inacceptable à l'ingestion de millions de chunks.
    # 3.6 car/token est la moyenne mesurée sur du français accentué (l'anglais
    # tourne autour de 4.0) : sous-estimer est le bon sens de l'erreur, un
    # chunk un peu court ne dépasse jamais la fenêtre de contexte.
    CHARS_PER_TOKEN: float = 3.6

    # ── Mémoire conversationnelle ───────────────────────────────────
    MEMORY_RECENT_MESSAGES: int = 20
    MEMORY_SUMMARY_TRIGGER: int = 40
    MEMORY_SUMMARY_MAX_TOKENS: int = 400

    # ── Ingestion ───────────────────────────────────────────────────
    INGEST_BATCH_SIZE: int = 32
    INGEST_MAX_FILE_MB: int = 512
    JOSHUA_LIBRARY_PATH: str = ""

    # ── Sécurité ────────────────────────────────────────────────────
    ADMIN_TELEGRAM_IDS: str = ""
    MAX_USER_INPUT_CHARS: int = 4000

    # ── Divers ──────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    APP_ENV: Literal["dev", "prod"] = "dev"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_ids(self) -> frozenset[int]:
        """IDs administrateurs, tolérante aux espaces et aux virgules finales.

        Une entrée non numérique est ignorée silencieusement plutôt que de
        faire échouer le démarrage : une faute de frappe dans la liste des
        admins ne doit pas mettre le bot hors service pour tout le monde.
        """
        ids: set[int] = set()
        for brut in self.ADMIN_TELEGRAM_IDS.split(","):
            brut = brut.strip()
            if brut.lstrip("-").isdigit():
                ids.add(int(brut))
        return frozenset(ids)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """DSN asyncpg, construit ici pour n'exister qu'à un seul endroit."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """DSN psycopg pour Alembic et les scripts d'ingestion.

        Les migrations et l'ingestion massive sont synchrones par nature
        (un long traitement séquentiel) : leur imposer une boucle asyncio
        compliquerait le code sans rien accélérer.
        """
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def chunk_target_chars(self) -> int:
        return int(self.CHUNK_TARGET_TOKENS * self.CHARS_PER_TOKEN)

    @property
    def chunk_overlap_chars(self) -> int:
        return int(self.CHUNK_OVERLAP_TOKENS * self.CHARS_PER_TOKEN)

    @property
    def chunk_min_chars(self) -> int:
        return int(self.CHUNK_MIN_TOKENS * self.CHARS_PER_TOKEN)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instance unique.

    ``lru_cache`` plutôt qu'une variable de module : la construction reste
    paresseuse (les tests peuvent poser leurs variables d'environnement
    avant le premier appel) et ``get_settings.cache_clear()`` permet de
    réinitialiser proprement entre deux tests.
    """
    return Settings()  # type: ignore[call-arg]
