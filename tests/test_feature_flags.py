from nanobot.config.schema import Config


def test_flag_defaults():
    c = Config()
    assert c.features.structured_logging is True


def test_env_override(monkeypatch):
    monkeypatch.setenv("NANOBOT__FEATURES__STRUCTURED_LOGGING", "false")
    c = Config()
    assert c.features.structured_logging is False
