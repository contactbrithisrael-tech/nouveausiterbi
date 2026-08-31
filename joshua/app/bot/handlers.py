"""Traitement des messages : le chemin critique de Joshua.

Ordre des opérations, et pourquoi
---------------------------------
1. **Contexte de journalisation** — posé en premier pour que TOUTE ligne
   émise ensuite, y compris une erreur, porte l'identifiant de requête.
2. **Limitation de débit** — avant tout travail coûteux : refuser tôt est
   l'intérêt même de la limitation.
3. **Nettoyage de l'entrée** — avant qu'elle n'atteigne la base ou le prompt.
4. **Persistance du message utilisateur** — avant l'appel au modèle : si
   Claude échoue, la question reste dans l'historique et l'utilisateur peut
   simplement demander « reprends ».
5. **RAG puis génération.**
6. **Résumé éventuel** — en dernier, hors du chemin de réponse.

Gestion des erreurs
-------------------
Aucune trace technique n'atteint jamais Telegram : l'utilisateur reçoit une
phrase, le serveur conserve la pile complète. Une conversation privée n'est
pas un canal de débogage, et une stacktrace renseigne un attaquant sur les
versions et les chemins du serveur.
"""

from __future__ import annotations

import asyncio
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from app.ai.claude import ErreurClaude
from app.ai.prompts import SYSTEM_PROMPT, message_utilisateur
from app.ai.rag import citations_utilisees
from app.ai.context_builder import formater_sources
from app.bot.telegram import envoyer_reponse
from app.database.repository import (
    ajouter_message,
    obtenir_ou_creer_conversation,
    obtenir_ou_creer_utilisateur,
)
from app.database.session import session_async
from app.memory.conversation import charger_contexte_conversation
from app.memory.summary import resumer_si_necessaire
from app.security.sanitization import nettoyer_entree_utilisateur
from app.utils.logging import bind_request, clear_request, get_logger

log = get_logger(__name__)

MESSAGE_ERREUR = "Joshua rencontre momentanément un problème."


async def _indiquer_saisie(bot, chat_id: int, arret: asyncio.Event) -> None:
    """Maintient l'indicateur « écrit… » pendant la réflexion.

    Telegram efface cet indicateur au bout de ~5 s ; une réponse RAG + Claude
    en demande souvent 10 à 20. Sans ce rafraîchissement, l'utilisateur croit
    que le bot est mort et renvoie sa question — doublant la charge.
    """
    try:
        while not arret.is_set():
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.wait_for(arret.wait(), timeout=4.5)
    except asyncio.TimeoutError:
        pass
    except Exception:  # pragma: no cover - purement cosmétique
        pass


async def traiter_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return

    debut = time.perf_counter()
    utilisateur_tg = update.effective_user
    bind_request(telegram_user_id=utilisateur_tg.id if utilisateur_tg else None)

    settings = context.bot_data["settings"]
    limiteur = context.bot_data["rate_limiter"]
    rag = context.bot_data["rag"]
    claude = context.bot_data["claude"]

    try:
        autorise, attente = await limiteur.autoriser(utilisateur_tg.id)
        if not autorise:
            await update.message.reply_text(
                f"Trop de messages d'un coup. Réessayez dans {attente} seconde(s)."
            )
            return

        question = nettoyer_entree_utilisateur(update.message.text, settings.MAX_USER_INPUT_CHARS)
        if not question:
            return

        arret = asyncio.Event()
        tache_saisie = asyncio.create_task(
            _indiquer_saisie(context.bot, update.message.chat_id, arret)
        )

        try:
            async with session_async() as session:
                utilisateur = await obtenir_ou_creer_utilisateur(
                    session,
                    telegram_user_id=utilisateur_tg.id,
                    username=utilisateur_tg.username,
                    first_name=utilisateur_tg.first_name,
                    language_code=utilisateur_tg.language_code,
                )
                conversation = await obtenir_ou_creer_conversation(
                    session, utilisateur.id, update.message.chat_id
                )
                await ajouter_message(session, conversation.id, "user", question)
                historique = await charger_contexte_conversation(session, conversation, settings)
                conversation_id = conversation.id

            # Le RAG s'exécute hors transaction : il appelle le réseau
            # (embeddings, Qdrant) et garder une connexion PostgreSQL ouverte
            # pendant ce temps épuiserait le pool sous charge.
            contexte = await rag.recuperer(question)

            messages = historique + [
                {"role": "user", "content": message_utilisateur(question, contexte.contexte)}
            ]
            reponse = await claude.repondre(messages=messages, system=SYSTEM_PROMPT)

            texte = reponse.texte or "Je n'ai pas de réponse à formuler."
            utilisees = citations_utilisees(texte, contexte.sources)
            bloc_sources = formater_sources(contexte.sources, utilisees)
            if bloc_sources and "[1]" not in texte.split("\n")[-1]:
                texte = f"{texte}\n\nSources :\n{bloc_sources}"

        finally:
            arret.set()
            tache_saisie.cancel()

        await envoyer_reponse(update, texte, settings)

        duree = (time.perf_counter() - debut) * 1000
        async with session_async() as session:
            await ajouter_message(
                session,
                conversation_id,
                "assistant",
                texte,
                sources=[{"n": s.numero, "ref": s.libelle()} for s in contexte.sources] or None,
                tokens_in=reponse.tokens_in,
                tokens_out=reponse.tokens_out,
                latency_ms=duree,
            )

        log.info(
            "message_traite",
            duration_ms=round(duree, 1),
            sources=len(contexte.sources),
            candidats=contexte.candidats,
            tokens_in=reponse.tokens_in,
            tokens_out=reponse.tokens_out,
        )

        # Le résumé est déclenché APRÈS l'envoi : il ne doit jamais retarder
        # une réponse, et son échec est sans conséquence pour l'utilisateur.
        try:
            async with session_async() as session:
                conversation = await obtenir_ou_creer_conversation(
                    session, utilisateur.id, update.message.chat_id
                )
                await resumer_si_necessaire(session, conversation, settings, claude)
        except Exception as exc:
            log.warning("resume_post_reponse_echoue", error=str(exc))

    except ErreurClaude as exc:
        log.error("erreur_claude", error=str(exc.cause) if exc.cause else str(exc))
        await update.message.reply_text(exc.message_utilisateur)
    except Exception as exc:
        # Filet de sécurité : aucune exception ne doit remonter jusqu'à PTB,
        # qui la journaliserait sans jamais répondre à l'utilisateur.
        log.error("erreur_inattendue", error=str(exc), exc_info=True)
        try:
            await update.message.reply_text(MESSAGE_ERREUR)
        except Exception:  # pragma: no cover
            pass
    finally:
        clear_request()


def enregistrer_handlers(application: Application) -> None:
    """Le gestionnaire de texte est enregistré APRÈS les commandes.

    PTB évalue les gestionnaires dans l'ordre : un filtre « tout texte »
    placé avant les commandes intercepterait « /stats » et le traiterait
    comme une question ordinaire.
    """
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, traiter_message)
    )
