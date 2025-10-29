"""Tests for enterprise configuration loader."""

from pathlib import Path

import pytest

from smart_warehouse.enterprise.config.settings import get_settings


def test_settings_load_default_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default environment should combine base settings and dev overrides."""

    config_dir = tmp_path / "config"
    env_dir = config_dir / "environments"
    env_dir.mkdir(parents=True)

    (config_dir / "settings.yaml").write_text(
        """
        environment: dev
        grid:
          width: 10
          height: 8
          cell_size: 25
        mqtt:
          broker_host: base-broker
          port: 1883
        """,
        encoding="utf-8",
    )

    (env_dir / "dev.yaml").write_text(
        """
        mqtt:
          broker_host: dev-broker
        logging:
          level: DEBUG
        """,
        encoding="utf-8",
    )

    monkeypatch.setenv("SW_CONFIG_DIR", str(config_dir))
    monkeypatch.delenv("SW_ENVIRONMENT", raising=False)

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.environment == "dev"
    assert settings.grid.width == 10
    assert settings.grid.height == 8
    assert settings.grid.cell_size == 25
    assert settings.mqtt.broker_host == "dev-broker"
    assert settings.logging.level == "DEBUG"


def test_settings_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Environment variables should override YAML configuration."""

    config_dir = tmp_path / "config"
    env_dir = config_dir / "environments"
    env_dir.mkdir(parents=True)

    (config_dir / "settings.yaml").write_text(
        """
        environment: prod
        mqtt:
          broker_host: base
          port: 1883
        """,
        encoding="utf-8",
    )

    (env_dir / "prod.yaml").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("SW_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("SW_ENVIRONMENT", "prod")
    monkeypatch.setenv("SW_MQTT__PORT", "2883")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.environment == "prod"
    assert settings.mqtt.port == 2883
    assert settings.mqtt.broker_host == "base"


def test_settings_cache_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clearing the cache should re-read configuration files."""

    config_dir = tmp_path / "config"
    env_dir = config_dir / "environments"
    env_dir.mkdir(parents=True)

    (config_dir / "settings.yaml").write_text("{}", encoding="utf-8")
    (env_dir / "dev.yaml").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("SW_CONFIG_DIR", str(config_dir))
    monkeypatch.delenv("SW_ENVIRONMENT", raising=False)

    get_settings.cache_clear()
    first = get_settings()

    monkeypatch.setenv("SW_ENVIRONMENT", "qa")
    (env_dir / "qa.yaml").write_text(
        "logging:\n  level: WARNING\n",
        encoding="utf-8",
    )

    get_settings.cache_clear()
    second = get_settings()

    assert first.environment == "dev"
    assert second.environment == "qa"
    assert second.logging.level == "WARNING"