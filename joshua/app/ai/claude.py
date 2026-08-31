"""Client Anthropic.

Choix d'architecture
--------------------
* **Un seul client, réutilisé.** ``AsyncAnthropic`` gère un pool de
  connexions HTTP ; en instancier un par message annulerait ce bénéfice et
  multiplierait les poignées de main TLS.

* **Le nom du modèle vient de la configuration, nulle part ailleurs.** Aucune
  chaîne « claude-… » n'apparaît dans le code : changer de modèle est une
  modification du ``.env``, pas du programme.

* **Les erreurs sont traduites, pas propagées.** Les couches supérieures ne
  doivent pas connaître les types d'exception du SDK ; elles reçoivent une
  ``ErreurClaude`` porteuse d'un message déjà présentable, et la stacktrace
  reste dans les journaux.

* **Le nombre de tentatives est délégué au SDK.** Il implémente déjà un
  repli exponentiel respectant l'en-tête ``retry-after`` ; le réimplémenter
  produirait deux politiques de réessai superposées.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    RateLimitError,
)

from app.config import Settings
from app.utils.logging import get_logger

log = get_logger(__name__)


class ErreurClaude(Exception):
    """Erreur déjà traduite pour l'utilisateur final."""

    def __init__(self, message_utilisateur: str, cause: Exception | None = None) -> None:
        super().__init__(message_utilisateur)
        self.message_utilisateur = message_utilisateur
        self.cause = cause


@dataclass(slots=True)
class ReponseClaude:
    texte: str
    tokens_in: int
    tokens_out: int
    stop_reason: str | None


class ClientClaude:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.ANTHROPIC_TIMEOUT_SECONDS,
            max_retries=settings.ANTHROPIC_MAX_RETRIES,
        )

    @property
    def modele(self) -> str:
        return self._settings.ANTHROPIC_MODEL

    async def repondre(
        self,
        messages: Sequence[dict[str, Any]],
        system: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ReponseClaude:
        """Un appel, une réponse.

        ``system`` est passé en paramètre dédié et non comme premier message :
        c'est la seule forme que l'API traite réellement comme une instruction
        système, et donc la seule qui offre la résistance attendue face à une
        tentative d'injection venue du contexte.
        """
        try:
            reponse = await self._client.messages.create(
                model=self._settings.ANTHROPIC_MODEL,
                max_tokens=max_tokens or self._settings.ANTHROPIC_MAX_TOKENS,
                temperature=(
                    temperature if temperature is not None else self._settings.ANTHROPIC_TEMPERATURE
                ),
                system=system,
                messages=list(messages),
            )
        except RateLimitError as exc:
            log.warning("claude_rate_limit", error=str(exc))
            raise ErreurClaude(
                "Joshua reçoit trop de demandes en ce moment. Réessayez dans un instant.", exc
            ) from exc
        except APIConnectionError as exc:
            log.error("claude_connexion", error=str(exc))
            raise ErreurClaude("Joshua n'arrive pas à joindre son moteur de raisonnement.", exc) from exc
        except APIStatusError as exc:
            log.error("claude_status", status=exc.status_code, error=str(exc))
            raise ErreurClaude("Joshua rencontre momentanément un problème.", exc) from exc

        # Le SDK renvoie une liste de blocs ; seuls les blocs texte nous
        # intéressent ici (l'usage d'outils n'est pas activé).
        texte = "".join(bloc.text for bloc in reponse.content if getattr(bloc, "type", "") == "text")
        return ReponseClaude(
            texte=texte.strip(),
            tokens_in=reponse.usage.input_tokens,
            tokens_out=reponse.usage.output_tokens,
            stop_reason=reponse.stop_reason,
        )

    async def resumer(self, transcription: str, prompt: str, max_tokens: int) -> str:
        """Résumé d'historique.

        Température nulle : un résumé doit être reproductible et factuel ;
        la créativité y est un défaut, pas une qualité.
        """
        reponse = await self.repondre(
            messages=[{"role": "user", "content": transcription}],
            system=prompt,
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return reponse.texte

    async def fermer(self) -> None:
        await self._client.close()
