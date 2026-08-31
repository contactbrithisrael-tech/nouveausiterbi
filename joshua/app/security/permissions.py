"""Contrôle d'accès et limitation de débit.

Choix d'architecture
--------------------
* **La liste d'admins vient de la configuration, jamais de la base.** Un
  administrateur ne peut donc pas être ajouté par une requête : il faut un
  accès au ``.env`` et un redémarrage. C'est volontairement rigide — la
  compromission d'un compte Telegram ne doit pas permettre l'escalade.

* **Limitation de débit dans Redis, avec repli mémoire.** Redis permet un
  compteur partagé entre plusieurs instances du bot. S'il est indisponible,
  on retombe sur un compteur local : dégrader la protection est préférable à
  refuser tout service, la limitation n'étant pas ici une barrière de
  sécurité mais une protection de coût (chaque message consomme des jetons
  Anthropic).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.config import Settings
from app.utils.logging import get_logger

log = get_logger(__name__)


def est_admin(telegram_user_id: int, settings: Settings) -> bool:
    return telegram_user_id in settings.admin_ids


def exiger_admin(telegram_user_id: int, settings: Settings) -> bool:
    """Vérifie le droit et journalise les refus.

    Les tentatives d'accès administrateur sont tracées : c'est le seul
    signal disponible en cas de sondage du bot.
    """
    autorise = est_admin(telegram_user_id, settings)
    if not autorise:
        log.warning("admin_denied", telegram_user_id=telegram_user_id)
    return autorise


@dataclass
class _FenetreLocale:
    horodatages: list[float] = field(default_factory=list)


class RateLimiter:
    """Fenêtre glissante par utilisateur.

    Fenêtre glissante et non « seau à jetons » : le comportement est plus
    simple à expliquer à un utilisateur (« N messages par minute ») et ne
    demande aucun état à faire évoluer dans le temps.
    """

    def __init__(self, settings: Settings, redis_client=None) -> None:
        self._limite = max(1, settings.RATE_LIMIT_MESSAGES)
        self._fenetre = max(1, settings.RATE_LIMIT_WINDOW_SECONDS)
        self._redis = redis_client
        self._local: dict[int, _FenetreLocale] = {}

    async def autoriser(self, telegram_user_id: int) -> tuple[bool, int]:
        """Retourne ``(autorisé, secondes_avant_reessai)``."""
        if self._redis is not None:
            try:
                return await self._autoriser_redis(telegram_user_id)
            except Exception as exc:  # pragma: no cover - dépend de l'infra
                log.warning("ratelimit_redis_indisponible", error=str(exc))
        return self._autoriser_local(telegram_user_id)

    async def _autoriser_redis(self, telegram_user_id: int) -> tuple[bool, int]:
        cle = f"joshua:rl:{telegram_user_id}"
        # INCR puis EXPIRE au premier passage : deux commandes en pipeline,
        # donc un seul aller-retour réseau par message.
        pipe = self._redis.pipeline()
        pipe.incr(cle)
        pipe.ttl(cle)
        compte, ttl = await pipe.execute()
        if compte == 1 or ttl < 0:
            await self._redis.expire(cle, self._fenetre)
            ttl = self._fenetre
        if compte > self._limite:
            return False, max(1, int(ttl))
        return True, 0

    def _autoriser_local(self, telegram_user_id: int) -> tuple[bool, int]:
        maintenant = time.monotonic()
        fenetre = self._local.setdefault(telegram_user_id, _FenetreLocale())
        limite_basse = maintenant - self._fenetre
        fenetre.horodatages = [t for t in fenetre.horodatages if t > limite_basse]
        if len(fenetre.horodatages) >= self._limite:
            attente = int(self._fenetre - (maintenant - fenetre.horodatages[0])) + 1
            return False, max(1, attente)
        fenetre.horodatages.append(maintenant)
        return True, 0
