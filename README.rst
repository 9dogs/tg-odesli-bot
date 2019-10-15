===================
Telegram Odesli Bot
===================

Send a song link in any (supported) music streaming service and get back a
message with links in other services.

It's useful but still work in progress. Some turbulence is expected.

|azure| |codecov| |docker| |license|


What is it for?
===============

You love to share music with your friends (or be shared with), but you settled
in different streaming services? With the help of great Odesli_ (former Songlink)
service you can share any song link to the Bot and get all other links back in
reply.

The Bot works in group chats as well. It reacts only to messages with music
streaming links (it also skips messages marked with special token ``!skip``).
You can promote the Bot to group admin and it will delete original message to
not clutter up the chat.

Supported services
==================

Currently these services are supported:

- Deezer
- Google Music
- SoundCloud

Privacy considerations
======================

The Bot have to have access to messages to operate. It does not store nor
transfer messages anywhere. However, the only true way to be sure about that is
to read through source code in this repository **and** run your copy of the Bot
(see section below).

Run your own copy
=================

Prerequisites
-------------

You need bot token to run your copy of the Bot but don't worry, it's a peace of
cake. Follow the instructions_ to create a new bot (you can set a name and a
username to whatever you want). All you need is a string like
``110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`` - this is your bot token.

Bot looks for ``TG_ODESLI_BOT_TG_API_TOKEN`` environment variable so you
must set it either in shell or via ``.env`` file:

.. code-block:: shell

    TG_ODESLI_BOT_TG_API_TOKEN=<your_token> <bot_run_command>
    # OR
    echo "<your_token>" > .env

Run with python
---------------

Clone the repo, `install pipenv <https://github.com/pypa/pipenv#installation>`_,
copy ``.env`` file into root directory and run the Bot (python 3.7 required):

.. code-block:: shell

    git clone https://github.com/9dogs/tg-odesli-bot.git
    cd tg-odesli-bot
    cp /path/to/.env ./
    pipenv run python tg-odesli-bot/bot.py
    # OR
    TG_ODESLI_BOT_TG_API_TOKEN=<your_token> pipenv run python tg-odesli-bot/bot.py

Run with Docker
---------------

Set ``TG_ODESLI_BOT_TG_API_TOKEN`` environment variable and run the image
(in order to use ``.env`` file mount it to ``/opt/tg_odesli_bot/.env``):

.. code-block:: shell

    docker run --rm -it -v /path/to/.env:/opt/tg_odesli_bot/.env 9dogs/tg_odesli_bot
    # OR
    TG_ODESLI_BOT_TG_API_TOKEN=<your_token> docker run 9dogs/tg_odesli_bot


.. |azure| image:: https://dev.azure.com/hellishbot/tg-odesli-bot/_apis/build/status/9dogs.tg-odesli-bot?branchName=master
           :target: https://dev.azure.com/hellishbot/tg-odesli-bot/
           :alt: Azure Pipeline status for master branch
.. |codecov| image:: https://codecov.io/gh/9dogs/tg-odesli-bot/branch/master/graph/badge.svg?token=3nWZWJ3Bl3
             :target: https://codecov.io/gh/9dogs/tg-odesli-bot
             :alt: codecov.io status for master branch
.. |docker| image:: https://img.shields.io/docker/automated/9dogs/tg-odesli-bot
            :alt: Docker Automated build

.. |license| image:: https://img.shields.io/badge/License-GPLv3-blue.svg
             :target: https://www.gnu.org/licenses/gpl-3.0
             :alt: License: GPL v3


.. _instructions: https://core.telegram.org/bots#6-botfather
.. _Odesli: https://odesli.co/
