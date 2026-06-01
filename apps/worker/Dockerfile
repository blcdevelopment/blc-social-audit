FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fontconfig \
        fonts-dejavu-core \
        libffi8 \
        libgdk-pixbuf-2.0-0 \
        libharfbuzz-subset0 \
        libjpeg62-turbo \
        libopenjp2-7 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY . .
RUN uv pip install --system -e .
RUN python -m playwright install --with-deps chromium chromium-headless-shell

CMD ["celery", "-A", "apps.worker.celery_app.celery_app", "worker", "--loglevel=info"]
