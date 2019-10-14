==========
Odesli Bot
==========

Send a song link in any (supported) music streaming service and get back a
message with links in other services.

It's useful but still work in progress. Some turbulence is expected.

|azure| |codecov| |docker|


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

The bot have to have access to messages to operate. It does not store nor
transfer messages anywhere. However, the only true way to be sure about that is
to read through source code in this repository **and** run your copy of the bot
(see section below).

Run your own copy
=================

Prerequisites
-------------

You need bot token to run your copy of the Bot but don't worry, it's peace of
cake. Follow instructions_ to create a new bot (you can set a name and an
username to whatever you want). All you need is a string like
``110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`` - this is your bot token.

Then before starting the Bot you must set ``GROUP_SONGLINK_BOT_BOT_API_TOKEN``
environment variable either in shell or in ``.env`` file:

.. code-block:: shell

    echo "<your_token>" > .env

Run with python
---------------

Clone the repo, `install pipenv <https://github.com/pypa/pipenv#installation>`_
copy ``.env`` file into root directory and run the bot (python 3.7 required):

.. code-block:: shell

    git clone https://github.com/9dogs/group-songlink-bot.git
    cd group-songlink-bot
    cp /path/to/.env ./
    pipenv run python group-songlink-bot/bot.py
    # OR
    GROUP_SONGLINK_BOT_BOT_API_TOKEN=<your_token> pipenv run python group-songlink-bot/bot.py

Run with Docker
---------------

Set ``GROUP_SONGLINK_BOT_BOT_API_TOKEN`` environment variable and run the image:

.. code-block:: shell

    echo "<your_token>" > .env
    docker run --rm -it 9dogs/group_songlink_bot
    # OR
    GROUP_SONGLINK_BOT_BOT_API_TOKEN=<your_token> docker run 9dogs/group_songlink_bot


.. |azure| image:: https://dev.azure.com/hellishbot/group-songlink-bot/_apis/build/status/9dogs.group-songlink-bot?branchName=master
           :target: https://dev.azure.com/hellishbot/group-songlink-bot/
           :alt: Azure Pipeline status for master branch
.. |codecov| image:: https://codecov.io/gh/9dogs/group-songlink-bot/branch/master/graph/badge.svg?token=3nWZWJ3Bl3
             :target: https://codecov.io/gh/9dogs/group-songlink-bot
             :alt: codecov.io status for master branch
.. |docker| image:: https://img.shields.io/docker/automated/9dogs/group_songlink_bot
            :alt: Docker Automated build

.. _instructions: https://core.telegram.org/bots#6-botfather
.. _Odesli: https://odesli.co/
