"""Point d'entrée : FastAPI + bot Telegram dans un même processus.

Pourquoi un seul processus
--------------------------
Le bot et l'API partagent exactement les mêmes dépendances coûteuses : le
modèle d'embeddings (~1 Go en mémoire), le pool PostgreSQL, les clients
Qdrant et Redis. Les séparer en deux conteneurs doublerait cette empreinte
pour aucun bénéfice à cette échelle. FastAPI apporte ici ce que le bot seul
n'a pas : une sonde de santé exploitable par Docker et un point d'entrée
webhook prêt à l'emploi.

Cycle de vie
------------
Tout est construit dans le ``lifespan`` : les dépendances sont créées avant
que le premier message n'arrive et libérées à l'arrêt. Rien n'est initialisé
à l'import d'un module — un import ne doit jamais ouvrir de connexion, sous
peine de rendre les tests impossibles à écrire.

Polling et webhook
------------------
En polling, PTB est démarré comme tâche de fond de l'application ASGI. En
webhook, la route ``/telegram/webhook`` injecte les mises à jour dans la MÊME
application. Les gestionnaires, eux, ne changent pas d'une ligne.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response

from app.ai.claude import ClientClaude
from app.ai.rag import MoteurRAG
from app.bot.telegram import construire_application
from app.config import get_settings
from app.database.session import fermer_async_engine, init_async_engine, session_async
from app.embeddings.base import get_embedding_provider
from app.security.auth import LimiteurTentatives, MagasinPostgres
from app.security.permissions import RateLimiter
from app.utils.logging import configure_logging, get_logger
from app.vectorstore.qdrant import QdrantRecherche

log = get_logger(__name__)


async def _creer_redis(settings) -> Any:
    """Client Redis, ou ``None`` si indisponible.

    Redis n'est utilisé que pour le cache et la limitation de débit : son
    absence dégrade le service, elle ne doit pas l'empêcher de démarrer.
    """
    try:
        from redis.asyncio import from_url

        client = from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        log.info("redis_connecte")
        return client
    except Exception as exc:
        log.warning("redis_indisponible", error=str(exc))
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, settings.LOG_JSON)
    log.info("demarrage", env=settings.APP_ENV, mode=settings.TELEGRAM_MODE, model=settings.ANTHROPIC_MODEL)

    init_async_engine(settings)
    redis_client = await _creer_redis(settings)

    provider = get_embedding_provider(settings)
    recherche = QdrantRecherche(settings)
    rag = MoteurRAG(settings, provider, recherche, redis_client)
    claude = ClientClaude(settings)
    limiteur = RateLimiter(settings, redis_client)

    application = construire_application(
        settings,
        {
            "settings": settings,
            "rag": rag,
            "claude": claude,
            "recherche": recherche,
            "rate_limiter": limiteur,
            "provider": provider,
            # Persistance des modes en base : c'est ce qui fait survivre une
            # authentification à un redémarrage et à plusieurs instances du bot.
            "modes": MagasinPostgres(),
            "auth_limiter": LimiteurTentatives(
                settings.AUTH_MAX_TENTATIVES, settings.AUTH_FENETRE_SECONDES
            ),
        },
    )

    app.state.settings = settings
    app.state.application = application
    app.state.recherche = recherche
    app.state.redis = redis_client

    await application.initialize()
    await application.start()

    if settings.TELEGRAM_MODE == "polling":
        # drop_pending_updates : au redémarrage, les messages reçus pendant
        # l'indisponibilité sont abandonnés. Y répondre plusieurs heures plus
        # tard serait plus déroutant qu'utile.
        await application.updater.start_polling(drop_pending_updates=True)
        log.info("telegram_polling_demarre")
    else:
        await application.bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
        log.info("telegram_webhook_configure", url=settings.TELEGRAM_WEBHOOK_URL)

    try:
        yield
    finally:
        log.info("arret_en_cours")
        if settings.TELEGRAM_MODE == "polling" and application.updater.running:
            await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await claude.fermer()
        await recherche.fermer()
        if redis_client is not None:
            await redis_client.aclose()
        await fermer_async_engine()
        log.info("arret_termine")


app = FastAPI(title="Joshua", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Sonde de santé, utilisée par Docker et la supervision.

    Elle vérifie les dépendances RÉELLES plutôt que de renvoyer « ok » :
    une sonde qui répond toujours vrai ne sert à rien. Le service reste
    déclaré sain si Qdrant est momentanément absent — le bot peut encore
    converser, sans documents — mais l'état est reporté.
    """
    etat = {"service": "joshua", "status": "ok"}
    try:
        etat["qdrant"] = await app.state.recherche.sante()
    except Exception:
        etat["qdrant"] = False
    try:
        async with session_async() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))
        etat["postgres"] = True
    except Exception:
        etat["postgres"] = False
        etat["status"] = "degraded"
    etat["redis"] = app.state.redis is not None
    return etat


@app.post("/telegram/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    """Point d'entrée webhook.

    Le jeton secret est vérifié avant tout traitement : sans lui, n'importe
    qui connaissant l'URL pourrait injecter de fausses mises à jour et faire
    parler le bot au nom d'un tiers.
    """
    settings = app.state.settings
    if settings.TELEGRAM_MODE != "webhook":
        raise HTTPException(status_code=404, detail="Mode webhook désactivé")
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Jeton invalide")

    from telegram import Update

    donnees = await request.json()
    mise_a_jour = Update.de_json(donnees, app.state.application.bot)
    # Traitement en tâche de fond : Telegram réémet toute mise à jour non
    # acquittée en quelques secondes. Répondre 200 immédiatement évite les
    # doublons quand une réponse demande vingt secondes.
    asyncio.create_task(app.state.application.process_update(mise_a_jour))
    return Response(status_code=200)


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_config=None,  # la journalisation est déjà configurée par structlog
    )


if __name__ == "__main__":
    main()
