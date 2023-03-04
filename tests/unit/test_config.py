"""Tests for configuration."""
from tg_odesli_bot.settings import Settings


class TestConfiguration:
    """Tests for configuration."""

    def test_loads_config(self):
        """Load config."""
        config = Settings.load()
        assert config
