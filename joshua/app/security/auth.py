"""Modes d'accès de Joshua : public, Frère/Sœur, Souverain Grand Commandeur.

Règle fondatrice
----------------
**Le modèle de langage ne décide JAMAIS d'une authentification.** Claude ne
voit ni le mot de passe, ni le fait qu'une tentative a eu lieu. La
comparaison est faite ici, en Python, sur une valeur lue dans
l'environnement ; le résultat est un booléen que le code — et lui seul —
transforme en changement d'état.

Un LLM à qui l'on confie « vérifie si ce mot de passe est correct » peut être
convaincu du contraire par la phrase suivante. Cette responsabilité ne lui
est donc pas confiée du tout.

Où vit l'état, et pourquoi
--------------------------
Le mode est une propriété **de l'utilisateur**, persistée dans PostgreSQL.
Trois alternatives ont été écartées :

* ``context.user_data`` de python-telegram-bot : perdu au redémarrage, et non
  partagé entre deux instances du bot. C'est la cause classique du symptôme
  « le mot de passe est accepté mais /mode affiche encore public » ;
* une variable globale : mêmes défauts, plus un risque de fuite d'un
  utilisateur à l'autre ;
* Redis seul : parfait comme cache, mais un ``FLUSHALL`` ou une éviction
  mémoire déconnecterait silencieusement tout le monde.

La base est donc la source de vérité. Une lecture par commande est
négligeable devant l'appel au modèle qui suit.

Comparaison des secrets
-----------------------
``hmac.compare_digest`` et non ``==`` : l'égalité de chaînes s'arrête au
premier caractère différent, ce qui laisse mesurer la longueur du préfixe
correct et rend le secret devinable caractère par caractère.
"""

from __future__ import annotations

import enum
import hmac
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.utils.logging import get_logger

log = get_logger(__name__)


class Mode(str, enum.Enum):
    """Niveaux d'accès, du plus ouvert au plus restreint."""

    PUBLIC = "public"
    FF = "ff"
    SGC = "sgc"

    @property
    def libelle(self) -> str:
        return {
            Mode.PUBLIC: "🟢 Mode actuel : Public (profane)",
            Mode.FF: "🟡 Mode actuel : Frère/Sœur",
            Mode.SGC: "🔴 Mode actuel : SGC",
        }[self]


#: Ordre d'habilitation : un mode donne accès à son niveau et à tous ceux qui
#: le précèdent. Exprimer la hiérarchie une fois évite les comparaisons
#: dispersées (« if mode == SGC or mode == FF ») qui finissent par diverger.
HIERARCHIE: tuple[Mode, ...] = (Mode.PUBLIC, Mode.FF, Mode.SGC)


def niveau(mode: Mode) -> int:
    return HIERARCHIE.index(mode)


def verifier_mot_de_passe(mode: Mode, fourni: str, settings: Any) -> bool:
    """Compare le mot de passe fourni au secret configuré.

    Un secret vide **n'authentifie jamais** : sans cette garde, un ``.env``
    incomplet ouvrirait le mode SGC à quiconque envoie « /sgc » suivi d'une
    chaîne vide — l'échec le plus silencieux qui soit.
    """
    attendu = {
        Mode.SGC: settings.JOSHUA_SGC_PASSWORD,
        Mode.FF: settings.JOSHUA_FF_PASSWORD,
    }.get(mode, "")

    if not attendu or not fourni:
        return False
    return hmac.compare_digest(fourni.encode("utf-8"), attendu.encode("utf-8"))


@dataclass
class _Tentatives:
    horodatages: list[float] = field(default_factory=list)


class LimiteurTentatives:
    """Freine les essais de mot de passe, par utilisateur.

    Un mot de passe partagé et court est devinable par force brute en
    quelques milliers d'essais ; Telegram permet de les envoyer en quelques
    minutes. La limitation ne remplace pas un bon secret, elle rend l'attaque
    bruyante et lente.

    L'état est en mémoire : un redémarrage le remet à zéro. C'est acceptable
    (le redémarrage n'est pas déclenchable par un attaquant) et cela évite de
    faire dépendre l'authentification de la disponibilité de Redis.
    """

    def __init__(self, maximum: int = 5, fenetre_secondes: int = 900) -> None:
        self._max = max(1, maximum)
        self._fenetre = max(1, fenetre_secondes)
        self._par_utilisateur: dict[int, _Tentatives] = {}

    def autorise(self, telegram_user_id: int) -> tuple[bool, int]:
        maintenant = time.monotonic()
        etat = self._par_utilisateur.setdefault(telegram_user_id, _Tentatives())
        limite_basse = maintenant - self._fenetre
        etat.horodatages = [t for t in etat.horodatages if t > limite_basse]
        if len(etat.horodatages) >= self._max:
            attente = int(self._fenetre - (maintenant - etat.horodatages[0])) + 1
            return False, max(1, attente)
        return True, 0

    def enregistrer_echec(self, telegram_user_id: int) -> None:
        """Seuls les ÉCHECS sont comptés.

        Compter les réussites punirait un utilisateur légitime qui se
        reconnecte souvent, sans gêner un attaquant — qui, lui, n'a que des
        échecs.
        """
        self._par_utilisateur.setdefault(telegram_user_id, _Tentatives()).horodatages.append(
            time.monotonic()
        )

    def reinitialiser(self, telegram_user_id: int) -> None:
        self._par_utilisateur.pop(telegram_user_id, None)


class MagasinModes(Protocol):
    """Contrat de persistance du mode.

    L'interface existe pour que les gestionnaires Telegram soient testables
    sans PostgreSQL : les tests injectent ``MagasinMemoire``, la production
    injecte ``MagasinPostgres``. Le code des commandes est identique dans les
    deux cas — c'est ce qui donne sa valeur au test.
    """

    async def lire(self, telegram_user_id: int) -> Mode: ...

    async def ecrire(self, telegram_user_id: int, mode: Mode) -> None: ...


class MagasinMemoire:
    """Implémentation de test. Non utilisée en production : elle perdrait
    l'état au redémarrage, précisément le défaut que l'on corrige."""

    def __init__(self) -> None:
        self._modes: dict[int, Mode] = {}

    async def lire(self, telegram_user_id: int) -> Mode:
        return self._modes.get(telegram_user_id, Mode.PUBLIC)

    async def ecrire(self, telegram_user_id: int, mode: Mode) -> None:
        self._modes[telegram_user_id] = mode


class MagasinPostgres:
    """Persistance réelle : une colonne sur la table ``users``."""

    async def lire(self, telegram_user_id: int) -> Mode:
        from app.database.repository import lire_mode
        from app.database.session import session_async

        async with session_async() as session:
            valeur = await lire_mode(session, telegram_user_id)
        try:
            return Mode(valeur)
        except ValueError:
            # Valeur inconnue en base (migration partielle, écriture manuelle) :
            # on retombe sur le mode le MOINS privilégié. En cas de doute sur
            # une habilitation, le doute ne profite jamais à l'accès.
            log.warning("mode_inconnu_en_base", valeur=valeur, telegram_user_id=telegram_user_id)
            return Mode.PUBLIC

    async def ecrire(self, telegram_user_id: int, mode: Mode) -> None:
        from app.database.repository import definir_mode
        from app.database.session import session_async

        async with session_async() as session:
            await definir_mode(session, telegram_user_id, mode.value)


def filtres_documentaires(mode: Mode) -> dict[str, Any] | None:
    """Restriction appliquée à la recherche documentaire selon le mode.

    Formulée en EXCLUSION (``must_not``) et non en inclusion, pour une raison
    de sûreté sur les données existantes : les documents déjà indexés ne
    portent pas de champ ``access_level``. Un filtre d'inclusion
    (« access_level = public ») les rendrait tous invisibles d'un coup, y
    compris pour les profanes — une panne totale déguisée en fonctionnalité.
    Avec une exclusion, un document sans niveau déclaré reste visible de tous,
    et seuls les documents explicitement marqués sont réservés.

    Le marquage se fait à l'ingestion (``--access ff`` / ``--access sgc``).
    Tant qu'aucun document n'est marqué, les trois modes voient la même chose :
    le mécanisme est en place, il n'ampute rien.
    """
    if mode is Mode.SGC:
        return None
    interdits = [m.value for m in HIERARCHIE if niveau(m) > niveau(mode)]
    return {"__must_not__": {"access_level": interdits}}
