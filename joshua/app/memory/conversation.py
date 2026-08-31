"""Mémoire conversationnelle : ce que Claude reçoit du passé.

Le problème
-----------
Renvoyer tout l'historique à chaque message a un coût qui croît linéairement
et sans limite : au centième échange, on paierait 99 messages inutiles pour
en traiter un. Ne rien renvoyer rendrait Joshua amnésique entre deux phrases.

La solution retenue est un compromis à deux étages, standard mais rarement
implémenté proprement :

* les ``MEMORY_RECENT_MESSAGES`` derniers messages, mot pour mot — c'est là
  que se trouvent les références implicites (« et pour le second ? ») ;
* un résumé des échanges plus anciens, régénéré périodiquement — il préserve
  le fil sans en payer le volume.

Le coût du contexte devient ainsi borné, quelle que soit l'ancienneté de la
conversation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Conversation, Message
from app.database.repository import messages_recents


def construire_historique(
    messages: list[Message], resume: str | None
) -> list[dict[str, Any]]:
    """Convertit l'historique en messages au format de l'API Anthropic.

    Deux règles imposées par l'API, et qu'il faut faire respecter ici plutôt
    que de découvrir en production :

    * les rôles doivent ALTERNER — deux messages « user » consécutifs (cas
      réel : l'utilisateur écrit trois fois d'affilée) sont fusionnés ;
    * l'historique doit commencer par un message « user ».

    Le résumé est injecté comme premier tour de parole plutôt que dans le
    prompt système : le système décrit le comportement de Joshua, pas l'état
    d'une conversation particulière. Les mélanger rendrait le prompt système
    dépendant de l'utilisateur, donc non partageable et non cacheable.
    """
    historique: list[dict[str, Any]] = []

    if resume:
        historique.append(
            {"role": "user", "content": f"[Résumé des échanges précédents]\n{resume}"}
        )
        historique.append(
            {"role": "assistant", "content": "Compris, je tiens compte de ce contexte."}
        )

    for message in messages:
        role = "assistant" if message.role == "assistant" else "user"
        contenu = (message.content or "").strip()
        if not contenu:
            continue
        if historique and historique[-1]["role"] == role:
            historique[-1]["content"] += "\n\n" + contenu
            continue
        historique.append({"role": role, "content": contenu})

    while historique and historique[0]["role"] != "user":
        historique.pop(0)

    return historique


async def charger_contexte_conversation(
    session: AsyncSession, conversation: Conversation, settings: Settings
) -> list[dict[str, Any]]:
    """Historique prêt à être envoyé, résumé compris."""
    messages = await messages_recents(
        session,
        conversation.id,
        limite=settings.MEMORY_RECENT_MESSAGES,
        apres_id=conversation.summary_until_message_id,
    )
    return construire_historique(messages, conversation.summary)
