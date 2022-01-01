# Telegram Odesli Bot

Send a song link in any (supported) music streaming service and get back
a message with links in other services.

Add in Telegram: [@odesli\_bot](https://t.me/odesli_bot)

It's useful but still work in progress. Some turbulence is expected.

[![PyPI](https://img.shields.io/pypi/v/tg-odesli-bot?color=blue)](https://pypi.org/project/tg-odesli-bot/)
[![Azure build status](https://dev.azure.com/9dogs/tg-odesli-bot/_apis/build/status/9dogs.tg-odesli-bot?branchName=master)](https://github.com/9dogs/tg-odesli-bot)
[![Code coverage](https://codecov.io/gh/9dogs/tg-odesli-bot/branch/master/graph/badge.svg?token=3nWZWJ3Bl3)](https://codecov.io/gh/9dogs/tg-odesli-bot)
[![Supported versions](https://img.shields.io/badge/python-3.7%20|%203.8%20|%203.9%20|%203.10-blue)](https://github.com/9dogs/tg-odesli-bot)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Codestyle: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## What is it for?

You love to share music with your friends (or be shared with), but you
settled in different streaming services? With the help of this bot you
can share any song link to the Bot and get all other links back in
reply.

Powered by the great [Odesli](https://odesli.co/) (former Songlink) service.

You can message the bot directly, invite it to group chats or use an inline
mode (type `@odesli_bot <URL>`). In group chats the bot will react only to
messages with music streaming links (it will also skip messages marked with
special token `!skip`). You can promote the bot to a group admin and it
will remove original message so that the chat remains tidy.

Original message           |  Bot's replay
:-------------------------:|:-------------------------:
<img alt="Original message" title="Original message" src="https://user-images.githubusercontent.com/432235/67324149-0a2b2580-f51c-11e9-8ce2-033cdf2d6628.png" height="200px">  | <img alt="Bot's reply" title="Bot's reply" src="https://user-images.githubusercontent.com/432235/67324159-0dbeac80-f51c-11e9-834a-7d4831a661d8.png" height="200px">

## Features

- Inline mode
- Private chat mode
- Group chat mode

## Supported services

Currently the following services are supported:

  - Deezer
  - Google Music
  - SoundCloud
  - Yandex Music
  - Spotify
  - YouTube Music
  - YouTube
  - Apple Music
  - Tidal

## Privacy considerations

The bot have to have access to messages in group chats to operate (that
is, it operates with disabled [privacy
mode](https://core.telegram.org/bots#privacy-mode)). It does not store
nor transfer messages anywhere. However, the only way to be completely
private is to read through source code in this repository **and** run
your copy of the bot (see section below). Or simply create a special
group only for music sharing and where no sensitive information will be
posted.

## Running your own copy

### Prerequisites

You need a Telegram [bot
token](https://core.telegram.org/bots/api#authorizing-your-bot) to run
your copy of the bot. Don't worry, it can be obtained easily. Follow the
[instructions](https://core.telegram.org/bots#6-botfather) to create a
new bot (you can set a name and a username to whatever you want). All you
need is a string like `110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw` -
this is your new bot token.

Additionally, disable privacy mode for your bot in a dialog with
@BotFather: "Group Privacy" - "Turn off" (that is for the bot to be able
to read group messages).

Bot from this repository will looks for `TG_ODESLI_BOT_TG_API_TOKEN`
environment variable on start, thus you must set it either in shell or
via `.env` file:

```console
$ echo "<your_token>" > .env
$ # OR
$ TG_ODESLI_BOT_TG_API_TOKEN=<your_token> <bot_run_command (see below)>
```

Ones you obtain a Telegram bot token, you can run bot using either Python
(3.7 or 3.8) or Docker.

### Run PyPI version

Create virtual environment, install `tg-odesli-bot` package and run the bot
with `tg-odesli-bot` command:

```console
$ python -m venv botenv
$ source botenv/bin/activate
$ pip install tg-odesli-bot
$ TG_ODESLI_BOT_TG_API_TOKEN=<your_token> tg-odesli-bot
```

### Run with Docker

Set `TG_ODESLI_BOT_TG_API_TOKEN` environment variable and run the image
`9dogs/tg-odesli-bot` (in order to use the `.env` file, mount it to
`/opt/tg-odesli-bot/.env`):

```console
$ docker run --rm -it -v /path/to/.env:/opt/tg-odesli-bot/.env 9dogs/tg-odesli-bot
# OR
$ TG_ODESLI_BOT_TG_API_TOKEN=<your_token> docker run -it --rm 9dogs/tg-odesli-bot
```


### Run version from the repository

Clone this repository, [install
poetry](https://python-poetry.org/docs/#installation), copy `.env` file
into the project's root directory and run the bot:

```console
$ git clone https://github.com/9dogs/tg-odesli-bot.git && cd tg-odesli-bot
# Install dependencies
$ poetry install
# If you have token in .env file
$ cp /path/to/.env ./
$ poetry run tg-odesli-bot
# If you specify token via shell env var
$ TG_ODESLI_BOT_TG_API_TOKEN=<your_token> poetry run tg-odesli-bot
```

## Contributing

Contributions are welcome via GitHub pull requests. The easiest way to bootstrap
development environment is to build `builder` target of Docker image:
```console
$ git clone https://github.com/9dogs/tg-odesli-bot.git && cd tg-odesli-bot
$ docker build -t 9dogs/tg-odesli-bot:dev --target=builder --build-arg poetry_args= .
```
Then you can run a shell inside the container:
```console
$ docker run -it --rm -v %cd%:/opt/tg-odesli-bot -v /opt/tg-odesli-bot/.venv 9dogs/tg-odesli-bot:dev bash
(container)$ make lint test
```
