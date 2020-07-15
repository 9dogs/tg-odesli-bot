"""Tests for configuration."""
from tg_odesli_bot.config import Config, TestConfig


class TestConfiguration:
    """Tests for configuration."""

    def test_loads_config(self):
        """Load config."""
        config = Config.load()
        assert config

    def test_loads_config_with_dotenv_file(self, test_dotenv):
        """Load config with variables from .env file."""
        config = Config.load()
        assert config
        assert config.TG_API_TOKEN == '1:test_token'

    def test_does_not_override_in_test_mode(self, test_dotenv):
        """Do not override config variables in test mode."""
        config = TestConfig.load()
        assert config.TG_API_TOKEN == '1:test_token'
