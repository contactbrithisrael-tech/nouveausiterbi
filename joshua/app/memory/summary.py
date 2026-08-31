"""Résumé périodique de l'historique.

Quand résumer
-------------
Le résumé est déclenché quand le nombre de messages postérieurs au dernier
résumé dépasse ``MEMORY_SUMMARY_TRIGGER``. Il n'est PAS déclenché à chaque
message : chaque résumé est un appel facturé, et résumer trop souvent
dégrade la mémoire (un résumé de résumé perd de l'information à chaque
passe).

Quand ne PAS résumer
--------------------
Un échec de résumé n'interrompt jamais la conversation : la conséquence est
un contexte un peu plus long au message suivant, ce que l'utilisateur ne
perçoit même pas. C'est le type d'opération qui doit échouer en silence.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.claude import ClientClaude
from app.ai.prompts import PROMPT_RESUME
from app.config import Settings
from app.database.models import Conversation
from app.database.repository import (
    compter_messages_conversation,
    enregistrer_resume,
    messages_recents,
)
from app.utils.logging import get_logger

log = get_logger(__name__)


async def resumer_si_necessaire(
    session: AsyncSession,
    conversation: Conversation,
    settings: Settings,
    claude: ClientClaude,
) -> bool:
    """Résume l'historique ancien si le seuil est franchi.

    Retourne ``True`` si un résumé a été produit.
    """
    total = await compter_messages_conversation(session, conversation.id)
    deja_resume = conversation.summary_until_message_id or 0
    messages = await messages_recents(
        session, conversation.id, limite=settings.MEMORY_SUMMARY_TRIGGER * 2, apres_id=deja_resume
    )
    if len(messages) < settings.MEMORY_SUMMARY_TRIGGER:
        return False

    # Seuls les messages qui SORTIRONT de la fenêtre récente sont résumés :
    # résumer aussi les messages encore transmis mot pour mot ferait payer
    # deux fois la même information.
    a_resumer = messages[: -settings.MEMORY_RECENT_MESSAGES] or messages
    transcription = "\n".join(
        f"{'Utilisateur' if m.role == 'user' else 'Joshua'} : {m.content}" for m in a_resumer
    )
    if not transcription.strip():
        return False

    try:
        resume = await claude.resumer(
            transcription, PROMPT_RESUME, settings.MEMORY_SUMMARY_MAX_TOKENS
        )
    except Exception as exc:
        log.warning("resume_echoue", conversation_id=conversation.id, error=str(exc))
        return False

    if conversation.summary:
        # Le résumé précédent est concaténé puis re-résumé au prochain
        # passage : on ne perd pas le passé lointain d'un coup.
        resume = f"{conversation.summary}\n\n{resume}"

    await enregistrer_resume(session, conversation.id, resume, a_resumer[-1].id)
    log.info(
        "resume_enregistre",
        conversation_id=conversation.id,
        messages_resumes=len(a_resumer),
        total=total,
    )
    return True
