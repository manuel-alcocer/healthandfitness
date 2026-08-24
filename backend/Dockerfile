# Backend image: Django + gunicorn.
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies resolve from pyproject alone, so this layer survives code edits.
COPY pyproject.toml ./
RUN uv venv /opt/venv && VIRTUAL_ENV=/opt/venv uv pip install -r pyproject.toml

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

RUN useradd --system --create-home --shell /usr/sbin/nologin django

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=django:django . .

# Static files are only the admin's; collected at build time so the container
# starts read-only.
RUN SECRET_KEY=build-only DEBUG=False python manage.py collectstatic --noinput \
    && chown -R django:django /app/staticfiles

USER django
EXPOSE 8000

# Two workers per replica; scale with replicas, not workers.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
