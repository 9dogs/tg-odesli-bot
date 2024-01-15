FROM python:3.11.7-bookworm AS builder

LABEL maintainer="Mikhail.Knyazev@phystech.edu"
LABEL description="Telegram Bot to share music with Odesli (former Songlink) service."

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ARG poetry_args='--without dev'

# Install & config poetry
RUN pip install poetry \
    && poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true
WORKDIR /opt/tg-odesli-bot
# Install project dependencies
COPY poetry.lock pyproject.toml /opt/tg-odesli-bot/
WORKDIR /opt/tg-odesli-bot
RUN poetry install --no-interaction --no-ansi $poetry_args
# Copy project files
COPY . /opt/tg-odesli-bot
ENV PYTHONPATH "${PYTHONPATH}:/opt/tg-odesli-bot"


FROM python:3.11.7-slim-bookworm

ARG UID=997
ARG GID=997

# Create user and group
RUN groupadd -g $GID -r bot \
    && useradd -u $UID -r -s /sbin/nologin -g bot bot
USER bot
# Copy project files
COPY --from=builder --chown=bot:bot /opt/tg-odesli-bot /opt/tg-odesli-bot
WORKDIR /opt/tg-odesli-bot
ENV PYTHONPATH "${PYTHONPATH}:/opt/tg-odesli-bot"

CMD ["/opt/tg-odesli-bot/.venv/bin/python", "-m", "tg_odesli_bot.bot"]
