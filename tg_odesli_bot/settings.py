"""Bot configuration."""
from __future__ import annotations

import logging.config

import sentry_sdk
import structlog
from aiocache import caches
from pydantic_settings import BaseSettings
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from structlog_sentry import SentryProcessor

RendererT = structlog.processors.JSONRenderer | structlog.dev.ConsoleRenderer


class Settings(BaseSettings):
    """Bot configuration."""

    #: Debug
    DEBUG: bool = False
    #: Telegram bot API key
    TG_API_TOKEN: str
    #: Odesli API URL
    ODESLI_API_URL: str = 'https://api.song.link/v1-alpha.1/links'
    #: Odesli API key
    ODESLI_API_KEY: str | None = None
    #: Sentry DSN
    SENTRY_DSN: str | None = None
    #: Sentry environment
    SENTRY_ENVIRONMENT: str = 'production'
    #: Spotify client ID
    SPOTIFY_CLIENT_ID: str
    #: Spotify client secret
    SPOTIFY_CLIENT_SECRET: str

    #: Logging configuration
    LOG_CONFIG: dict = {
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
    LOG_RENDERER: RendererT = structlog.processors.JSONRenderer()

    # Cache config
    caches.set_config(
        {
            'default': {
                'ttl': 18000,  # 300 min
                'cache': 'aiocache.SimpleMemoryCache',
                'serializer': {
                    'class': 'aiocache.serializers.PickleSerializer'
                },
            }
        }
    )

    class Config:
        """Settings."""

        env_file = '.env'
        env_prefix = 'TG_ODESLI_BOT_'

    def init_logging(self) -> None:
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
                structlog.processors.UnicodeDecoder(),
                SentryProcessor(
                    level=logging.WARNING, tag_keys=['status_code']
                ),
                structlog.processors.format_exc_info,
                self.LOG_RENDERER,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    @classmethod
    def load(cls) -> Settings:
        """Load config and init logging.

        :returns: a config object
        """
        config = cls()
        if config.SENTRY_DSN:
            sentry_sdk.init(
                dsn=config.SENTRY_DSN,
                integrations=[AioHttpIntegration()],
                environment=config.SENTRY_ENVIRONMENT,
            )
        if not structlog.is_configured():
            config.init_logging()
        return config


class TestSettings(Settings):
    """Testing configuration."""

    #: Testing mode
    TESTING: bool = True
    #: Debug
    DEBUG: bool = True
    #: Telegram bot API key
    TG_API_TOKEN: str = '1:test_token'
    #: Sentry DSN
    SENTRY_DSN: str | None = None
    #: Spotify client ID
    SPOTIFY_CLIENT_ID: str = 'test_id'
    #: Spotify client secret
    SPOTIFY_CLIENT_SECRET: str = 'test_secret'

    class Config:
        """Settings."""

        env_file = None
