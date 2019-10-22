===================
Telegram Odesli Bot
===================

Send a song link in any (supported) music streaming service and get back a
message with links in other services.

Add in Telegram: `@odesli_bot <t.me/odesli_bot>`_

It's useful but still work in progress. Some turbulence is expected.

|azure| |codecov| |docker| |license| |black|


What is it for?
===============

You love to share music with your friends (or be shared with), but you settled
in different streaming services? With the help of this bot you can share any
song link to the Bot and get all other links back in reply.

Powered by the great Odesli_ (former Songlink) service.

The bot works in group chats as well. It reacts only to messages with music
streaming links (it also skips messages marked with special token ``!skip``).
You can promote the bot to a group admin and it will remove original message
so that the chat remains tidy.

|before_pic| |after_pic|

Supported services
==================

Currently the following services are supported:

- Deezer
- Google Music
- SoundCloud
- Yandex Music
- Spotify
- Youtube Music

Privacy considerations
======================

The bot have to have access to messages in group chats to operate (that is, it
operates with disabled `privacy mode <https://core.telegram.org/bots#privacy-mode>`_).
It does not store nor transfer messages anywhere. However, the only way to be completely
private is to read through source code in this repository **and** run your copy of the bot
(see section below). Or simply create a special group only for music sharing and where no
sensitive information will be posted.

Running your own copy
=====================

Prerequisites
-------------

You need a Telegram `bot token <https://core.telegram.org/bots/api#authorizing-your-bot>`_
to run your copy of the bot. Don't worry, it can be obtained easily. Follow the instructions_
to create a new bot (you can set a name and a username to whatever you want). All you need
is a string like ``110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`` - this is your new bot token.

Additionally, disable privacy mode for your bot in a dialog with @BotFather:
"Group Privacy" - "Turn off" (that is for the bot to be able to read group
messages).

Bot from this repository will looks for ``TG_ODESLI_BOT_TG_API_TOKEN`` environment variable
on start, thus you must set it either in shell or via ``.env`` file:

.. code-block:: console

    $ echo "<your_token>" > .env
    $ # OR
    $ TG_ODESLI_BOT_TG_API_TOKEN=<your_token> <bot_run_command (see below)>

One you obtain a Telegram bot token, you can run bot using either Python or Docker.

Run with Python
---------------

Clone this repository, `install pipenv <https://github.com/pypa/pipenv#installation>`_,
copy ``.env`` file into the project's root directory and run the bot (Python 3.7 required):

.. code-block:: console

    $ git clone https://github.com/9dogs/tg-odesli-bot.git
    $ cd tg-odesli-bot
    $ # If you have token in .env file
    $ cp /path/to/.env ./
    $ PYTHONPATH=. pipenv run bot
    $ # If you specify token via shell env var
    $ PYTHONPATH=. TG_ODESLI_BOT_TG_API_TOKEN=<your_token> pipenv run bot

Run with Docker
---------------

Set ``TG_ODESLI_BOT_TG_API_TOKEN`` environment variable and run the image ``9dogs/tg-odesli-bot``
(in order to use ``.env`` file, mount it to ``/opt/tg-odesli-bot/.env``):

.. code-block:: console

    $ TG_ODESLI_BOT_TG_API_TOKEN=<your_token> docker run 9dogs/tg-odesli-bot
    $ # OR
    $ docker run --rm -it -v /path/to/.env:/opt/tg-odesli-bot/.env 9dogs/tg-odesli-bot


.. |azure| image:: https://dev.azure.com/9dogs/tg-odesli-bot/_apis/build/status/9dogs.tg-odesli-bot?branchName=master
           :target: https://dev.azure.com/9dogs/tg-odesli-bot/
           :alt: Azure Pipeline status for master branch
.. |codecov| image:: https://codecov.io/gh/9dogs/tg-odesli-bot/branch/master/graph/badge.svg?token=3nWZWJ3Bl3
             :target: https://codecov.io/gh/9dogs/tg-odesli-bot
             :alt: codecov.io status for master branch
.. |docker| image:: https://img.shields.io/docker/cloud/automated/9dogs/tg-odesli-bot
            :target: https://hub.docker.com/r/9dogs/tg-odesli-bot
            :alt: Docker Automated build

.. |license| image:: https://img.shields.io/badge/License-GPLv3-blue.svg
             :target: https://www.gnu.org/licenses/gpl-3.0
             :alt: License: GPL v3

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
           :target: https://github.com/psf/black
           :alt: Codestyle Black

.. |before_pic| raw:: html

                <img title="before" src="https://user-images.githubusercontent.com/432235/67324149-0a2b2580-f51c-11e9-8ce2-033cdf2d6628.png" height="200px">

.. |after_pic| raw:: html

                <img title="after" src="https://user-images.githubusercontent.com/432235/67324159-0dbeac80-f51c-11e9-834a-7d4831a661d8.png" height="200px">


.. _instructions: https://core.telegram.org/bots#6-botfather
.. _Odesli: https://odesli.co/
