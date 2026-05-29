FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY . .
RUN uv pip install --system -e .
RUN python -m playwright install --with-deps chromium chromium-headless-shell

CMD ["celery", "-A", "apps.worker.celery_app.celery_app", "worker", "--loglevel=info"]
