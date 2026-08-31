"""Droits d'administration et limitation de débit."""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings
from app.security.permissions import RateLimiter, est_admin, exiger_admin


def _settings(admins: str, **extra) -> Settings:
    get_settings.cache_clear()
    return Settings(
        TELEGRAM_BOT_TOKEN="t", ANTHROPIC_API_KEY="k", ADMIN_TELEGRAM_IDS=admins, **extra
    )


def test_liste_admins_multiple():
    s = _settings("111,222,333")
    assert s.admin_ids == frozenset({111, 222, 333})


def test_liste_admins_tolere_espaces_et_virgules():
    s = _settings(" 111 , 222 ,, ")
    assert s.admin_ids == frozenset({111, 222})


def test_entree_invalide_ignoree_sans_planter():
    """Une faute de frappe ne doit pas empêcher le bot de démarrer."""
    s = _settings("111,abc,222")
    assert s.admin_ids == frozenset({111, 222})


def test_liste_vide():
    s = _settings("")
    assert s.admin_ids == frozenset()
    assert est_admin(111, s) is False


def test_admin_reconnu_et_refuse():
    s = _settings("111")
    assert est_admin(111, s) is True
    assert est_admin(999, s) is False
    assert exiger_admin(999, s) is False


async def test_rate_limit_local_bloque_au_dela_du_seuil():
    s = _settings("1", RATE_LIMIT_MESSAGES=3, RATE_LIMIT_WINDOW_SECONDS=60)
    limiteur = RateLimiter(s, redis_client=None)
    for _ in range(3):
        autorise, _ = await limiteur.autoriser(42)
        assert autorise
    autorise, attente = await limiteur.autoriser(42)
    assert autorise is False
    assert attente >= 1


async def test_rate_limit_est_par_utilisateur():
    s = _settings("1", RATE_LIMIT_MESSAGES=1)
    limiteur = RateLimiter(s, redis_client=None)
    assert (await limiteur.autoriser(1))[0] is True
    assert (await limiteur.autoriser(2))[0] is True  # un autre utilisateur
    assert (await limiteur.autoriser(1))[0] is False


async def test_rate_limit_bascule_en_local_si_redis_casse():
    """Redis en panne dégrade la protection, il ne coupe pas le service."""

    class RedisCasse:
        def pipeline(self):
            raise ConnectionError("redis down")

    s = _settings("1", RATE_LIMIT_MESSAGES=2)
    limiteur = RateLimiter(s, redis_client=RedisCasse())
    assert (await limiteur.autoriser(7))[0] is True
    assert (await limiteur.autoriser(7))[0] is True
    assert (await limiteur.autoriser(7))[0] is False
