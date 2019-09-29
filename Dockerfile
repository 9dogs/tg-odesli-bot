FROM python:3.7-stretch AS builder

ARG pipenv_install_args="--deploy"

# Install Pipenv
RUN curl https://raw.githubusercontent.com/pypa/pipenv/master/get-pipenv.py | python
WORKDIR /opt/group_songlink_bot
# Install project dependencies
ENV PIPENV_VENV_IN_PROJECT 1
COPY Pipfile* ./
RUN pipenv install $pipenv_install_args
# Copy project files
COPY . /opt/group_songlink_bot
# Remove Python cache and auxilary files
RUN find -L /opt/group_songlink_bot -type d -name __pycache__ -prune -exec rm -rf {} \; \
    && find -L /opt/group_songlink_bot -maxdepth 1 -type f,d \
            ! -path /opt/group_songlink_bot \
            ! -name 'group_songlink_bot' \
            ! -name '.venv' \
        -exec rm -rf {} \;

FROM python:3.7-slim-stretch

ARG UID=997
ARG GID=997

# Create user and group
RUN groupadd -g $GID -r bot \
    && useradd -u $UID -r -s /sbin/nologin -g bot bot
USER bot
# Copy project files
COPY --from=builder --chown=bot:bot /opt/group_songlink_bot /opt/group_songlink_bot

ENV PYTHONPATH "${PYTHONPATH}:/opt/group_songlink_bot"

WORKDIR /opt/group_songlink_bot
CMD ["/opt/group_songlink_bot/.venv/bin/python", "group_songlink_bot/bot.py"]
