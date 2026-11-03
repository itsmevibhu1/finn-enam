FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 finn

WORKDIR /app
COPY --chown=finn:finn scripts/ scripts/
COPY --chown=finn:finn config/ config/
COPY --chown=finn:finn data/ data/
COPY --chown=finn:finn dist/ dist/
COPY --chown=finn:finn .openai/hosting.json .openai/hosting.json
USER finn
EXPOSE 10000
CMD ["python3", "scripts/serve.py", "--host", "0.0.0.0"]
