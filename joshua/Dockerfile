# ═══════════════════════════════════════════════════════════════
# Joshua — image applicative
#
# Construction en deux étapes : les dépendances sont compilées dans une
# première image (qui garde les outils de build), puis seul le résultat est
# copié. L'image finale ne contient aucun compilateur — moins de poids et
# moins de surface d'attaque.
# ═══════════════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential est nécessaire à certaines roues sans binaire précompilé
# pour cette architecture. Il reste dans CETTE étape uniquement.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Cache des modèles FastEmbed : monté en volume pour ne télécharger le
    # modèle (~1 Go) qu'une seule fois, et non à chaque reconstruction.
    FASTEMBED_CACHE_PATH=/models

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Utilisateur non privilégié : un processus exposé au réseau ne tourne pas
# en root. Il possède /models et /app/data, seuls emplacements où il écrit.
RUN useradd --create-home --uid 1000 joshua \
    && mkdir -p /models /app/data/incoming /app/data/processed \
    && chown -R joshua:joshua /models /app

WORKDIR /app
COPY --chown=joshua:joshua . .

USER joshua

EXPOSE 8000

# La sonde interroge /health, qui vérifie réellement PostgreSQL et Qdrant :
# un conteneur « vivant » mais incapable de répondre doit être vu comme tel.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["python", "-m", "app.main"]
