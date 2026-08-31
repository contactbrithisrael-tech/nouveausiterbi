"""Couche Telegram : construction de l'application et envoi des réponses.

Polling ou webhook, sans réécriture
-----------------------------------
``construire_application`` retourne toujours la même ``Application`` PTB, avec
les mêmes gestionnaires. Seul le mode de RÉCEPTION change :

* ``polling`` — le bot interroge Telegram ; aucune URL publique nécessaire,
  idéal en développement ;
* ``webhook`` — Telegram appelle une route FastAPI qui injecte la mise à jour
  dans la même application (voir ``app/main.py``).

Le passage de l'un à l'autre est un changement de variable d'environnement.
C'est précisément ce que le cahier des charges demande : ne pas avoir à
réécrire le bot le jour du passage en production.

Découpage des messages
----------------------
Telegram rejette tout message dépassant 4096 caractères. Un découpage naïf
tous les 4096 caractères coupe au milieu d'un mot, d'une URL ou d'un bloc de
code — et un bloc de code coupé casse le rendu Markdown de TOUS les messages
suivants. ``decouper_message`` respecte donc, dans l'ordre : les blocs de
code, les paragraphes, les lignes, les phrases, puis les espaces.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import Application, ApplicationBuilder

from app.config import Settings
from app.utils.logging import get_logger

log = get_logger(__name__)

#: Marge sous la limite de 4096 : les indicateurs de continuité et les
#: fermetures de blocs de code ajoutés au découpage doivent tenir.
MARGE = 64

_BLOC_CODE = re.compile(r"```")


def _sous_decouper(texte: str, taille: int) -> list[str]:
    """Découpe un fragment sans jamais couper au milieu d'un mot.

    Les séparateurs sont essayés du plus structurant au moins structurant :
    couper entre deux paragraphes est invisible, couper entre deux mots est
    acceptable, couper au milieu d'un mot ne l'est pas.
    """
    if len(texte) <= taille:
        return [texte] if texte else []

    morceaux: list[str] = []
    reste = texte
    while len(reste) > taille:
        fenetre = reste[:taille]
        coupe = -1
        for separateur in ("\n\n", "\n", ". ", " ! ", " ? ", " "):
            position = fenetre.rfind(separateur)
            # 40 % : en dessous, la coupure produirait un fragment ridicule ;
            # mieux vaut alors descendre au séparateur suivant.
            if position > taille * 0.4:
                coupe = position + len(separateur)
                break
        if coupe <= 0:
            coupe = taille
        morceaux.append(reste[:coupe].rstrip())
        reste = reste[coupe:].lstrip()
    if reste:
        morceaux.append(reste)
    return morceaux


def decouper_message(texte: str, limite: int = 4096) -> list[str]:
    """Découpe une réponse en messages Telegram valides.

    Les blocs de code sont traités comme des unités : s'il faut couper à
    l'intérieur, le fragment est refermé par ``` et le suivant rouvert avec
    ```. Sans cela, tout le reste de la conversation s'affiche en
    chasse fixe, et Telegram peut rejeter le message pour Markdown invalide.
    """
    texte = (texte or "").strip()
    if not texte:
        return []
    taille = max(256, limite - MARGE)
    if len(texte) <= taille:
        return [texte]

    resultats: list[str] = []
    # Un split sur ``` donne alternativement du texte normal (indices pairs)
    # et du code (indices impairs).
    segments = _BLOC_CODE.split(texte)
    for i, segment in enumerate(segments):
        est_code = i % 2 == 1
        if not segment.strip():
            continue
        if est_code:
            for morceau in _sous_decouper(segment, taille - 8):
                resultats.append(f"```{morceau}```")
        else:
            resultats.extend(_sous_decouper(segment, taille))
    return [r for r in resultats if r.strip()]


async def envoyer_reponse(
    update: Update, texte: str, settings: Settings, parse_mode: str | None = None
) -> None:
    """Envoie une réponse, découpée si nécessaire.

    ``parse_mode`` est None par défaut, et c'est délibéré : le texte produit
    par un modèle contient régulièrement des caractères que Telegram
    interprète comme du Markdown mal formé (un astérisque isolé, un souligné
    dans un nom de fichier). Telegram rejette alors le message ENTIER. Envoyer
    en texte brut garantit la livraison ; le rendu est un confort, la
    livraison est la fonction.
    """
    if update.message is None:
        return
    for morceau in decouper_message(texte, settings.TELEGRAM_MAX_MESSAGE_CHARS):
        try:
            await update.message.reply_text(morceau, parse_mode=parse_mode)
        except BadRequest as exc:
            # Repli en texte brut : la cause la plus fréquente est un balisage
            # invalide, et le message doit partir malgré tout.
            log.warning("telegram_bad_request", error=str(exc))
            try:
                await update.message.reply_text(morceau, parse_mode=None)
            except TelegramError as exc2:
                log.error("telegram_envoi_impossible", error=str(exc2))
                return
        except RetryAfter as exc:
            # Limite de débit côté Telegram : on abandonne la suite plutôt que
            # d'endormir la boucle, ce qui bloquerait tous les autres
            # utilisateurs pendant plusieurs secondes.
            log.warning("telegram_retry_after", seconds=exc.retry_after)
            return
        except Forbidden:
            log.info("telegram_bloque_par_utilisateur")
            return


def construire_application(settings: Settings, donnees: dict[str, Any]) -> Application:
    """Construit l'application PTB et y attache les dépendances.

    Les dépendances (moteur RAG, client Claude, session…) passent par
    ``bot_data`` plutôt que par des variables globales : les gestionnaires
    restent testables en leur fournissant un dictionnaire, et rien n'est
    partagé implicitement entre deux instances.
    """
    from app.bot.commands import enregistrer_commandes
    from app.bot.handlers import enregistrer_handlers

    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)  # un message lent ne bloque pas les autres
        .build()
    )
    application.bot_data.update(donnees)
    enregistrer_commandes(application)
    enregistrer_handlers(application)
    return application
