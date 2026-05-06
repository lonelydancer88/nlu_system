"""Tests for Config - API key configuration management."""
import json
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestConfigDefaults:
    """Config should provide sensible defaults."""

    def test_default_amap_city(self):
        from config import Config
        cfg = Config()
        assert cfg.amap_city == "北京"

    def test_default_coffee_api_mode(self):
        from config import Config
        cfg = Config()
        assert cfg.coffee_api_mode == "mock"

    def test_default_ollama_model(self):
        from config import Config
        cfg = Config()
        assert cfg.ollama_model == "gemma4:e2b"

    def test_default_ollama_base_url(self):
        from config import Config
        cfg = Config()
        assert cfg.ollama_base_url == "http://localhost:11434/api/chat"

    def test_default_ollama_timeout(self):
        from config import Config
        cfg = Config()
        assert cfg.ollama_timeout == 120.0


class TestConfigFromEnv:
    """Config should load from environment variables."""

    def test_amap_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("AMAP_API_KEY", "test_key_123")
        from config import Config
        cfg = Config()
        assert cfg.amap_api_key == "test_key_123"

    def test_amap_key_alias(self, monkeypatch):
        """AMAP_KEY should work as alias for AMAP_API_KEY."""
        monkeypatch.delenv("AMAP_API_KEY", raising=False)
        monkeypatch.setenv("AMAP_KEY", "alias_key_456")
        from config import Config
        cfg = Config()
        assert cfg.amap_api_key == "alias_key_456"

    def test_amap_api_key_takes_precedence_over_amap_key(self, monkeypatch):
        """AMAP_API_KEY should take precedence over AMAP_KEY when both set."""
        monkeypatch.setenv("AMAP_API_KEY", "primary_key")
        monkeypatch.setenv("AMAP_KEY", "alias_key")
        from config import Config
        cfg = Config()
        assert cfg.amap_api_key == "primary_key"

    def test_amap_security_key_from_env(self, monkeypatch):
        """AMAP_SECURITY_KEY should be loaded into amap_security_key."""
        monkeypatch.setenv("AMAP_SECURITY_KEY", "security_key_789")
        from config import Config
        cfg = Config()
        assert cfg.amap_security_key == "security_key_789"

    def test_amap_city_from_env(self, monkeypatch):
        monkeypatch.setenv("AMAP_CITY", "上海")
        from config import Config
        cfg = Config()
        assert cfg.amap_city == "上海"

    def test_coffee_api_mode_from_env(self, monkeypatch):
        monkeypatch.setenv("COFFEE_API_MODE", "meituan")
        from config import Config
        cfg = Config()
        assert cfg.coffee_api_mode == "meituan"


class TestConfigFromFile:
    """Config should load from config.json."""

    def test_load_from_config_json(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "amap_api_key": "file_key_456",
            "amap_city": "深圳"
        }, ensure_ascii=False))
        monkeypatch.setenv("CONFIG_FILE", str(config_file))
        # Clear env vars that would override
        monkeypatch.delenv("AMAP_API_KEY", raising=False)
        monkeypatch.delenv("AMAP_KEY", raising=False)
        monkeypatch.delenv("AMAP_CITY", raising=False)
        from config import Config
        cfg = Config()
        assert cfg.amap_api_key == "file_key_456"
        assert cfg.amap_city == "深圳"


class TestConfigPriority:
    """Env vars should override config.json which should override defaults."""

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"amap_api_key": "from_file"}))
        monkeypatch.setenv("CONFIG_FILE", str(config_file))
        monkeypatch.setenv("AMAP_API_KEY", "from_env")
        from config import Config
        cfg = Config()
        assert cfg.amap_api_key == "from_env"

    def test_file_overrides_default(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"amap_city": "广州"}))
        monkeypatch.setenv("CONFIG_FILE", str(config_file))
        monkeypatch.delenv("AMAP_CITY", raising=False)
        from config import Config
        cfg = Config()
        assert cfg.amap_city == "广州"


class TestConfigValidation:
    """Config should validate required fields."""

    def test_missing_amap_key_raises(self, tmp_path, monkeypatch):
        # Use temp config file without amap_api_key
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"llm_api_key": "test"}))
        monkeypatch.setenv("CONFIG_FILE", str(config_file))
        monkeypatch.delenv("AMAP_API_KEY", raising=False)
        monkeypatch.delenv("AMAP_KEY", raising=False)
        from config import Config
        cfg = Config()
        with pytest.raises(ValueError, match="amap_api_key"):
            cfg.validate()

    def test_invalid_coffee_api_mode_raises(self, monkeypatch):
        monkeypatch.setenv("AMAP_API_KEY", "valid_key")
        monkeypatch.setenv("COFFEE_API_MODE", "invalid_mode")
        from config import Config
        cfg = Config()
        with pytest.raises(ValueError, match="coffee_api_mode"):
            cfg.validate()

    def test_valid_config_passes(self, monkeypatch):
        monkeypatch.setenv("AMAP_API_KEY", "valid_key")
        from config import Config
        cfg = Config()
        cfg.validate()  # Should not raise


class TestConfigKeyGuidance:
    """Config should provide guidance for obtaining API keys."""

    def test_missing_key_guidance(self, tmp_path, monkeypatch):
        # Use temp config file without amap_api_key
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"llm_api_key": "test"}))
        monkeypatch.setenv("CONFIG_FILE", str(config_file))
        monkeypatch.delenv("AMAP_API_KEY", raising=False)
        monkeypatch.delenv("AMAP_KEY", raising=False)
        from config import Config
        cfg = Config()
        guidance = cfg.get_missing_key_guidance()
        assert "amap" in guidance.lower()
        assert "lbs.amap.com" in guidance

    def test_all_keys_present_no_guidance(self, monkeypatch):
        monkeypatch.setenv("AMAP_API_KEY", "valid_key")
        from config import Config
        cfg = Config()
        guidance = cfg.get_missing_key_guidance()
        assert guidance == ""
