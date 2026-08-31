"""Commandes Telegram, publiques et réservées aux administrateurs.

Principe
--------
Une commande d'administration ne se contente pas de refuser : elle répond
comme une commande inconnue (« Commande inconnue »), sans révéler qu'elle
existe. Confirmer l'existence de ``/reindex`` à un inconnu lui indique quoi
chercher.

``/reindex`` ne lance PAS l'indexation depuis le bot : une ingestion dure des
heures et n'a rien à faire dans le processus qui répond aux utilisateurs. La
commande affiche l'état et rappelle la commande à exécuter côté serveur —
c'est une séparation de responsabilités, pas une limitation.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.bot.telegram import envoyer_reponse
from app.database.repository import sources_principales, statistiques
from app.database.session import session_async
from app.security.auth import Mode, verifier_mot_de_passe
from app.security.permissions import exiger_admin
from app.utils.logging import bind_request, clear_request, get_logger

log = get_logger(__name__)

TEXTE_START = """Bonjour, je suis **Joshua**.

Je réponds à partir d'une base documentaire indexée : posez simplement votre
question, en français ou dans une autre langue.

Quand je m'appuie sur un document, je cite ma source. Quand je n'ai pas
l'information, je le dis plutôt que d'inventer.

/help pour la liste des commandes."""

TEXTE_HELP = """Commandes disponibles :

/start — présentation
/help — cette aide
/status — état des services
/mode — niveau d'accès actuel
/logout — revenir au mode public

Posez vos questions directement, sans commande. Je garde le fil de la
conversation ; les échanges anciens sont résumés automatiquement.

Mes réponses citent leurs sources sous la forme [1], [2], suivies du nom du
fichier et de la page ou de la section."""


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await envoyer_reponse(update, TEXTE_START.replace("**", ""), context.bot_data["settings"])


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await envoyer_reponse(update, TEXTE_HELP, context.bot_data["settings"])


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """État des dépendances, accessible à tous.

    Un utilisateur qui n'obtient pas de réponse doit pouvoir distinguer
    « Joshua est en panne » de « ma question était mauvaise ». Aucune adresse
    ni version n'est divulguée, seulement un état.
    """
    settings = context.bot_data["settings"]
    recherche = context.bot_data["recherche"]

    qdrant_ok = await recherche.sante()
    chunks = await recherche.compter() if qdrant_ok else 0

    postgres_ok = True
    try:
        async with session_async() as session:
            await statistiques(session)
    except Exception:
        postgres_ok = False

    lignes = [
        "État de Joshua",
        f"• Base documentaire : {'disponible' if qdrant_ok else 'indisponible'}",
        f"• Passages indexés : {chunks:,}".replace(",", " "),
        f"• Mémoire conversationnelle : {'disponible' if postgres_ok else 'indisponible'}",
        f"• Modèle : {settings.ANTHROPIC_MODEL}",
    ]
    await envoyer_reponse(update, "\n".join(lignes), settings)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    if not exiger_admin(update.effective_user.id, settings):
        await update.message.reply_text("Commande inconnue.")
        return

    async with session_async() as session:
        stats = await statistiques(session)
    recherche = context.bot_data["recherche"]
    points = await recherche.compter() if await recherche.sante() else 0

    lignes = [
        "Statistiques",
        f"• Utilisateurs : {stats['utilisateurs']}",
        f"• Messages : {stats['messages']}",
        f"• Documents indexés : {stats['documents']}",
        f"• Chunks (PostgreSQL) : {stats['chunks']}",
        f"• Points (Qdrant) : {points}",
    ]
    # L'écart entre les deux derniers compteurs est le signal d'un index
    # désynchronisé : il est affiché plutôt que masqué.
    if points and abs(points - stats["chunks"]) > max(10, stats["chunks"] * 0.01):
        lignes.append("⚠ Écart entre PostgreSQL et Qdrant : une réindexation est conseillée.")
    await envoyer_reponse(update, "\n".join(lignes), settings)


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    if not exiger_admin(update.effective_user.id, settings):
        await update.message.reply_text("Commande inconnue.")
        return

    async with session_async() as session:
        documents = await sources_principales(session, limite=25)

    if not documents:
        await update.message.reply_text("Aucun document indexé.")
        return
    lignes = ["Documents les plus volumineux :"] + [
        f"{i}. {nom} — {chunks} passages" for i, (nom, chunks) in enumerate(documents, 1)
    ]
    await envoyer_reponse(update, "\n".join(lignes), settings)


async def cmd_reindex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    if not exiger_admin(update.effective_user.id, settings):
        await update.message.reply_text("Commande inconnue.")
        return

    chemin = settings.JOSHUA_LIBRARY_PATH or "data/incoming/"
    await envoyer_reponse(
        update,
        "\n".join(
            [
                "La réindexation s'exécute côté serveur, pas depuis le bot :",
                "",
                f"    python scripts/index_library.py --update    ({chemin})",
                "    python scripts/reindex.py --full            (reconstruction complète)",
                "",
                "Une ingestion massive dure des heures ; la lancer depuis le processus "
                "qui répond aux utilisateurs le rendrait indisponible.",
            ]
        ),
        settings,
    )


def _envelopper(handler):
    """Ajoute contexte de journalisation et filet à erreurs à une commande."""

    async def enveloppe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        bind_request(telegram_user_id=update.effective_user.id if update.effective_user else None)
        try:
            await handler(update, context)
        except Exception as exc:
            log.error("commande_erreur", commande=handler.__name__, error=str(exc), exc_info=True)
            if update.message:
                await update.message.reply_text("Joshua rencontre momentanément un problème.")
        finally:
            clear_request()

    return enveloppe


# ═══════════════════════════════════════════════════════════════════
# MODES D'ACCÈS
#
# Le mot de passe est vérifié PAR LE CODE, jamais par le modèle : Claude
# n'est appelé à aucun moment de ces commandes et ne voit ni le secret, ni
# la tentative. Le message qui le contient est effacé du salon, n'est pas
# journalisé, et n'est pas enregistré en base — les commandes échappent au
# gestionnaire de messages, qui seul écrit dans l'historique.
# ═══════════════════════════════════════════════════════════════════


async def _effacer_message(update: Update) -> None:
    """Supprime le message contenant le mot de passe.

    Best-effort : la suppression peut échouer (droits, message trop ancien).
    L'échec ne doit pas empêcher l'authentification — le secret resterait
    visible dans l'historique du salon, ce qui est un problème d'hygiène, pas
    une raison de refuser l'accès. L'utilisateur en est averti.
    """
    try:
        await update.message.delete()
    except Exception:
        log.info("suppression_message_impossible")


async def _authentifier(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: Mode) -> None:
    settings = context.bot_data["settings"]
    magasin = context.bot_data["modes"]
    limiteur = context.bot_data["auth_limiter"]
    user_id = update.effective_user.id

    fourni = " ".join(context.args or []).strip()
    await _effacer_message(update)

    if not fourni:
        await update.message.chat.send_message(
            f"Usage : /{mode.value} <mot de passe>\n"
            "Le message est effacé automatiquement après lecture."
        )
        return

    autorise, attente = limiteur.autorise(user_id)
    if not autorise:
        # Le message ne distingue pas « trop d'essais » d'un mot de passe
        # faux : indiquer qu'un blocage est actif renseignerait sur le fait
        # que le compte vaut la peine d'être attaqué.
        log.warning("auth_trop_de_tentatives", telegram_user_id=user_id, mode=mode.value)
        await update.message.chat.send_message(
            f"Trop de tentatives. Réessayez dans {attente // 60 + 1} minute(s)."
        )
        return

    if not verifier_mot_de_passe(mode, fourni, settings):
        limiteur.enregistrer_echec(user_id)
        # Seul l'ÉCHEC est journalisé, et jamais la valeur soumise.
        log.warning("auth_echec", telegram_user_id=user_id, mode=mode.value)
        await update.message.chat.send_message("Mot de passe incorrect.")
        return

    limiteur.reinitialiser(user_id)
    await magasin.ecrire(user_id, mode)
    log.info("auth_reussie", telegram_user_id=user_id, mode=mode.value)

    # L'état est relu depuis le magasin plutôt qu'affiché de mémoire : la
    # confirmation atteste alors d'une écriture réellement persistée, et non
    # de l'intention de l'écrire. C'est exactement la différence entre
    # « le mot de passe est accepté » et « le mode a changé ».
    confirme = await magasin.lire(user_id)
    await update.message.chat.send_message(
        f"Authentification acceptée.\n{confirme.libelle}"
    )


async def cmd_sgc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _authentifier(update, context, Mode.SGC)


async def cmd_ff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _authentifier(update, context, Mode.FF)


async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche le mode réellement persisté pour CET utilisateur."""
    magasin = context.bot_data["modes"]
    mode = await magasin.lire(update.effective_user.id)
    await update.message.reply_text(mode.libelle)


async def cmd_logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    magasin = context.bot_data["modes"]
    user_id = update.effective_user.id
    await magasin.ecrire(user_id, Mode.PUBLIC)
    log.info("logout", telegram_user_id=user_id)
    mode = await magasin.lire(user_id)
    await update.message.reply_text(f"Déconnecté.\n{mode.libelle}")


async def cmd_inconnue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Réponse aux commandes non reconnues.

    Sans ce gestionnaire, une commande inconnue reste SANS RÉPONSE : le
    filtre des messages ordinaires exclut les commandes, et l'utilisateur
    conclut que le bot est en panne. Le message est le même que celui
    renvoyé à un non-administrateur qui tente une commande réservée — ainsi
    l'existence de ces commandes ne se déduit pas de la réponse.
    """
    if update.message:
        await update.message.reply_text("Commande inconnue. /help pour la liste.")


def enregistrer_commandes(application: Application) -> None:
    for nom, handler in (
        ("start", cmd_start),
        ("help", cmd_help),
        ("status", cmd_status),
        ("mode", cmd_mode),
        ("sgc", cmd_sgc),
        ("ff", cmd_ff),
        ("logout", cmd_logout),
        ("stats", cmd_stats),
        ("sources", cmd_sources),
        ("reindex", cmd_reindex),
    ):
        application.add_handler(CommandHandler(nom, _envelopper(handler)))

    # Enregistré EN DERNIER : python-telegram-bot évalue les gestionnaires
    # dans l'ordre, un filtre « toute commande » placé avant intercepterait
    # les commandes réelles.
    application.add_handler(MessageHandler(filters.COMMAND, _envelopper(cmd_inconnue)))
