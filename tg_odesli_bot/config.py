"""Bot configuration."""
import logging.config
import os
from typing import Optional

import dotenv
import sentry_sdk
import structlog
from aiocache import caches
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from structlog_sentry import SentryJsonProcessor


class Config:
    """Bot configuration."""

    #: Debug
    DEBUG = False
    #: Telegram bot API key (required)
    TG_API_TOKEN = ''
    #: Odesli API URL (required)
    ODESLI_API_URL = 'https://api.song.link/v1-alpha.1/links'
    #: Odesli API key (optional)
    ODESLI_API_KEY: Optional[str] = ''
    #: Sentry DSN (optional)
    SENTRY_DSN: Optional[str] = ''

    #: Logging configuration
    LOG_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': (
                    '%(asctime)s - %(name)s - %(filename)s:%(lineno)d - '
                    '%(processName)s - %(levelname)s - %(message)s'
                )
            },
            'json': {'format': '%(message)s'},
        },
        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            },
            'stdout_json': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'json',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            'tg_odesli_bot': {'handlers': ['stdout_json'], 'level': 'INFO'},
            # asyncio warnings
            'asyncio': {'handlers': ['stdout'], 'level': 'WARNING'},
        },
    }
    #: Log renderer
    LOG_RENDERER = structlog.processors.JSONRenderer()

    # Cache config
    caches.set_config(
        {
            'default': {
                'ttl': 6000,  # 100 min
                'cache': 'aiocache.SimpleMemoryCache',
                'serializer': {
                    'class': 'aiocache.serializers.PickleSerializer'
                },
            }
        }
    )

    def init_logging(self):
        """Init logging."""
        if self.DEBUG:  # pragma: no cover
            self.LOG_CONFIG['loggers']['tg_odesli_bot']['level'] = 'DEBUG'
            if not isinstance(
                self.LOG_RENDERER, structlog.dev.ConsoleRenderer
            ):
                self.LOG_RENDERER = structlog.dev.ConsoleRenderer(pad_event=50)
        logging.config.dictConfig(self.LOG_CONFIG)
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt='iso'),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                SentryJsonProcessor(level=logging.WARNING),
                self.LOG_RENDERER,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    @classmethod
    def load(cls, env_prefix: str = 'TG_ODESLI_BOT_'):
        """Load config merging default variables and environment variables.

        :param env_prefix: prefix for environment variables
        :return: filled config object
        """
        config = cls()
        # Load environment from .env file
        dotenv.load_dotenv()
        # Update config object with environment variables
        for env_var_name, value in os.environ.items():
            if env_var_name.startswith(env_prefix):
                var_name = env_var_name[len(env_prefix) :]
                # Do not override config vars in testing mode
                if hasattr(config, 'TESTING') and hasattr(config, var_name):
                    continue
                setattr(config, var_name, value)
        if config.SENTRY_DSN:
            sentry_sdk.init(
                dsn=config.SENTRY_DSN, integrations=[AioHttpIntegration()]
            )
        if not structlog.is_configured():
            config.init_logging()
        return config


class TestConfig(Config):
    """Testing configuration."""

    #: Testing mode
    TESTING = True
    #: Debug
    DEBUG = True
    #: Telegram bot API key
    TG_API_TOKEN = 'invalid'
    #: Sentry DSN
    SENTRY_DSN = None
