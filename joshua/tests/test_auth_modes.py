"""Modes d'accès : validation, persistance, isolation entre utilisateurs.

Les sept scénarios demandés sont couverts, et testés SUR LES VRAIS
GESTIONNAIRES Telegram — pas sur une reproduction de leur logique. C'est la
seule façon de vérifier ce qui compte ici : que la commande écrit réellement
dans le magasin, et que ``/mode`` relit réellement ce qui a été écrit.

Le magasin est injecté (``MagasinMemoire``) ; PostgreSQL n'est donc pas
nécessaire, mais le code exécuté est celui de production.
"""

from __future__ import annotations

import pytest

from app.bot.commands import cmd_ff, cmd_logout, cmd_mode, cmd_sgc
from app.config import Settings, get_settings
from app.security.auth import (
    LimiteurTentatives,
    MagasinMemoire,
    Mode,
    filtres_documentaires,
    verifier_mot_de_passe,
)

MDP_SGC = "phrase-secrete-du-souverain-2026"
MDP_FF = "phrase-secrete-des-freres-2026"


def _settings(**extra) -> Settings:
    get_settings.cache_clear()
    return Settings(
        TELEGRAM_BOT_TOKEN="t",
        ANTHROPIC_API_KEY="k",
        JOSHUA_SGC_PASSWORD=MDP_SGC,
        JOSHUA_FF_PASSWORD=MDP_FF,
        **extra,
    )


class FauxChat:
    def __init__(self) -> None:
        self.envoyes: list[str] = []

    async def send_message(self, texte, **kwargs):
        self.envoyes.append(texte)


class FauxMessage:
    def __init__(self, chat: FauxChat) -> None:
        self.chat = chat
        self.reponses: list[str] = []
        self.supprime = False

    async def reply_text(self, texte, **kwargs):
        self.reponses.append(texte)

    async def delete(self):
        self.supprime = True


class FauxUtilisateur:
    def __init__(self, user_id: int) -> None:
        self.id = user_id
        self.username = f"u{user_id}"
        self.first_name = "Test"
        self.language_code = "fr"


class FauxUpdate:
    def __init__(self, user_id: int) -> None:
        self.effective_user = FauxUtilisateur(user_id)
        self.message = FauxMessage(FauxChat())

    @property
    def sorties(self) -> list[str]:
        """Tout ce que l'utilisateur a vu, quel que soit le canal d'envoi."""
        return self.message.reponses + self.message.chat.envoyes


class FauxContexte:
    def __init__(self, bot_data: dict, args: list[str] | None = None) -> None:
        self.bot_data = bot_data
        self.args = args or []


@pytest.fixture
def contexte():
    """Dépendances injectées, comme en production (voir app/main.py)."""
    return {
        "settings": _settings(),
        "modes": MagasinMemoire(),
        "auth_limiter": LimiteurTentatives(maximum=5, fenetre_secondes=900),
    }


# ── 1. Utilisateur public ───────────────────────────────────────────────


async def test_1_utilisateur_public_par_defaut(contexte):
    update = FauxUpdate(1001)
    await cmd_mode(update, FauxContexte(contexte))
    assert update.sorties == [Mode.PUBLIC.libelle]
    assert "Public (profane)" in update.sorties[0]


# ── 2. Mauvais mot de passe ─────────────────────────────────────────────


async def test_2_sgc_mauvais_mot_de_passe_reste_public(contexte):
    update = FauxUpdate(1002)
    await cmd_sgc(update, FauxContexte(contexte, ["mauvais-mot-de-passe"]))
    assert any("incorrect" in s.lower() for s in update.sorties)

    verif = FauxUpdate(1002)
    await cmd_mode(verif, FauxContexte(contexte))
    assert verif.sorties == [Mode.PUBLIC.libelle]


async def test_2bis_mot_de_passe_vide_refuse(contexte):
    """Le cas le plus dangereux : « /sgc » sans argument."""
    update = FauxUpdate(1003)
    await cmd_sgc(update, FauxContexte(contexte, []))
    assert await contexte["modes"].lire(1003) is Mode.PUBLIC


async def test_2ter_secret_non_configure_n_authentifie_jamais():
    """Un .env incomplet ne doit pas ouvrir le mode le plus privilégié."""
    settings = Settings(TELEGRAM_BOT_TOKEN="t", ANTHROPIC_API_KEY="k")
    assert verifier_mot_de_passe(Mode.SGC, "", settings) is False
    assert verifier_mot_de_passe(Mode.SGC, "n'importe quoi", settings) is False
    assert verifier_mot_de_passe(Mode.FF, "", settings) is False


# ── 3 et 4. Bon mot de passe, puis /mode ────────────────────────────────


async def test_3_sgc_bon_mot_de_passe_change_le_mode(contexte):
    update = FauxUpdate(1004)
    await cmd_sgc(update, FauxContexte(contexte, [MDP_SGC]))
    assert any("acceptée" in s for s in update.sorties)
    assert await contexte["modes"].lire(1004) is Mode.SGC


async def test_4_mode_apres_authentification_affiche_sgc(contexte):
    """Le scénario exact du bug signalé : /sgc accepté, puis /mode."""
    await cmd_sgc(FauxUpdate(1005), FauxContexte(contexte, [MDP_SGC]))

    update = FauxUpdate(1005)
    await cmd_mode(update, FauxContexte(contexte))
    assert update.sorties == ["🔴 Mode actuel : SGC"]


# ── 5. Déconnexion ──────────────────────────────────────────────────────


async def test_5_logout_revient_au_public(contexte):
    await cmd_sgc(FauxUpdate(1006), FauxContexte(contexte, [MDP_SGC]))
    await cmd_logout(FauxUpdate(1006), FauxContexte(contexte))

    update = FauxUpdate(1006)
    await cmd_mode(update, FauxContexte(contexte))
    assert update.sorties == ["🟢 Mode actuel : Public (profane)"]


# ── 6. Mode Frère/Sœur ──────────────────────────────────────────────────


async def test_6_ff_correct_donne_le_mode_frere_soeur(contexte):
    await cmd_ff(FauxUpdate(1007), FauxContexte(contexte, [MDP_FF]))

    update = FauxUpdate(1007)
    await cmd_mode(update, FauxContexte(contexte))
    assert update.sorties == ["🟡 Mode actuel : Frère/Sœur"]


async def test_6bis_les_mots_de_passe_ne_sont_pas_interchangeables(contexte):
    """Le mot de passe FF ne doit pas ouvrir le mode SGC."""
    await cmd_sgc(FauxUpdate(1008), FauxContexte(contexte, [MDP_FF]))
    assert await contexte["modes"].lire(1008) is Mode.PUBLIC


# ── 7. Isolation entre utilisateurs ─────────────────────────────────────


async def test_7_aucune_session_heritee_entre_utilisateurs(contexte):
    """La propriété la plus critique : le mode est attaché à UN identifiant."""
    await cmd_sgc(FauxUpdate(2001), FauxContexte(contexte, [MDP_SGC]))
    await cmd_ff(FauxUpdate(2002), FauxContexte(contexte, [MDP_FF]))

    for user_id, attendu in ((2001, Mode.SGC), (2002, Mode.FF), (2003, Mode.PUBLIC)):
        update = FauxUpdate(user_id)
        await cmd_mode(update, FauxContexte(contexte))
        assert update.sorties == [attendu.libelle], f"utilisateur {user_id}"

    # La déconnexion de l'un ne déclasse pas l'autre.
    await cmd_logout(FauxUpdate(2001), FauxContexte(contexte))
    assert await contexte["modes"].lire(2001) is Mode.PUBLIC
    assert await contexte["modes"].lire(2002) is Mode.FF


# ── Traitement du secret ────────────────────────────────────────────────


async def test_le_message_contenant_le_secret_est_efface(contexte):
    update = FauxUpdate(3001)
    await cmd_sgc(update, FauxContexte(contexte, [MDP_SGC]))
    assert update.message.supprime is True


async def test_le_secret_n_apparait_dans_aucune_reponse(contexte):
    for args in ([MDP_SGC], ["mauvais"], []):
        update = FauxUpdate(3002)
        await cmd_sgc(update, FauxContexte(contexte, args))
        assert all(MDP_SGC not in s for s in update.sorties)


async def test_comparaison_a_temps_constant_sur_prefixe(contexte):
    """Un préfixe correct ne doit pas être accepté."""
    settings = _settings()
    assert verifier_mot_de_passe(Mode.SGC, MDP_SGC[:-1], settings) is False
    assert verifier_mot_de_passe(Mode.SGC, MDP_SGC + "x", settings) is False
    assert verifier_mot_de_passe(Mode.SGC, MDP_SGC, settings) is True


async def test_limitation_des_tentatives(contexte):
    """Après N échecs, les essais suivants sont refusés sans être évalués."""
    contexte["auth_limiter"] = LimiteurTentatives(maximum=3, fenetre_secondes=900)
    for _ in range(3):
        await cmd_sgc(FauxUpdate(4001), FauxContexte(contexte, ["faux"]))

    update = FauxUpdate(4001)
    await cmd_sgc(update, FauxContexte(contexte, [MDP_SGC]))
    assert any("tentatives" in s.lower() for s in update.sorties)
    assert await contexte["modes"].lire(4001) is Mode.PUBLIC


async def test_une_reussite_reinitialise_le_compteur(contexte):
    contexte["auth_limiter"] = LimiteurTentatives(maximum=3, fenetre_secondes=900)
    await cmd_sgc(FauxUpdate(4002), FauxContexte(contexte, ["faux"]))
    await cmd_sgc(FauxUpdate(4002), FauxContexte(contexte, [MDP_SGC]))
    await cmd_logout(FauxUpdate(4002), FauxContexte(contexte))
    for _ in range(2):
        await cmd_sgc(FauxUpdate(4002), FauxContexte(contexte, ["faux"]))
    update = FauxUpdate(4002)
    await cmd_sgc(update, FauxContexte(contexte, [MDP_SGC]))
    assert await contexte["modes"].lire(4002) is Mode.SGC


async def test_la_limitation_est_par_utilisateur(contexte):
    contexte["auth_limiter"] = LimiteurTentatives(maximum=2, fenetre_secondes=900)
    for _ in range(2):
        await cmd_sgc(FauxUpdate(5001), FauxContexte(contexte, ["faux"]))
    await cmd_sgc(FauxUpdate(5002), FauxContexte(contexte, [MDP_SGC]))
    assert await contexte["modes"].lire(5002) is Mode.SGC


# ── Effet du mode sur la recherche documentaire ─────────────────────────


def test_filtres_par_mode():
    """Le mode restreint par EXCLUSION : un document non marqué reste visible.

    Un filtre d'inclusion masquerait tous les documents déjà indexés, qui ne
    portent pas de niveau d'accès — une panne totale déguisée en sécurité.
    """
    assert filtres_documentaires(Mode.SGC) is None
    assert filtres_documentaires(Mode.FF) == {"__must_not__": {"access_level": ["sgc"]}}
    assert filtres_documentaires(Mode.PUBLIC) == {"__must_not__": {"access_level": ["ff", "sgc"]}}


def test_filtre_qdrant_produit_bien_un_must_not():
    from app.vectorstore.qdrant import _construire_filtre

    filtre = _construire_filtre(filtres_documentaires(Mode.PUBLIC))
    assert filtre.must is None
    assert [c.key for c in filtre.must_not] == ["access_level"]


# ── Enregistrement effectif auprès de python-telegram-bot ───────────────


def test_les_commandes_sont_reellement_enregistrees():
    """Vérifie l'ENREGISTREMENT, pas seulement l'existence des fonctions.

    Le symptôme « Joshua ne reconnaît pas cette commande » vient toujours
    d'un gestionnaire écrit mais jamais ajouté à l'Application. Ce test
    construit la vraie Application et lit la liste des commandes qu'elle
    accepte réellement.
    """
    from telegram.ext import ApplicationBuilder, CommandHandler

    from app.bot.commands import enregistrer_commandes

    application = ApplicationBuilder().token("123456:jeton-de-test").build()
    enregistrer_commandes(application)

    enregistrees: set[str] = set()
    for groupe in application.handlers.values():
        for handler in groupe:
            if isinstance(handler, CommandHandler):
                enregistrees |= {str(c) for c in handler.commands}

    attendues = {"start", "help", "status", "mode", "sgc", "ff", "logout", "stats", "sources", "reindex"}
    assert attendues <= enregistrees, f"commandes manquantes : {attendues - enregistrees}"


async def test_commande_inconnue_recoit_une_reponse():
    """Une commande inconnue ne doit jamais rester sans réponse."""
    from app.bot.commands import cmd_inconnue

    update = FauxUpdate(6001)
    await cmd_inconnue(update, FauxContexte({}))
    assert update.sorties and "inconnue" in update.sorties[0].lower()
