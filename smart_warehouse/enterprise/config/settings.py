"""Unified configuration system for the Smart Warehouse platform.

This module centralises application settings using :mod:`pydantic-settings`.
Configuration values are assembled from (in order of precedence):

1. Explicit keyword arguments when instantiating :class:`AppSettings`.
2. Environment variables prefixed with ``SW_`` (supports nested fields using ``__``).
3. A ``.env`` file located at the project root.
4. YAML configuration files: ``config/settings.yaml`` (base) and
   ``config/environments/<environment>.yaml`` (environment-specific overrides).

All sources are deeply merged, making it straightforward to override only a
subset of settings per environment. The resulting configuration object is
validated and type-safe, providing convenient access across the codebase.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml
from pydantic import AnyUrl, BaseModel, Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
	"GridSettings",
	"TimingSettings",
	"ColorSettings",
	"MQTTSettings",
	"DatabaseSettings",
	"TelemetrySettings",
	"LoggingSettings",
	"AppSettings",
	"get_settings",
]


_ENVIRONMENT_VAR = "SW_ENVIRONMENT"
_CONFIG_DIR_ENV_VAR = "SW_CONFIG_DIR"


def _project_root() -> Path:
	"""Return the absolute project root directory."""

	return Path(__file__).resolve().parents[3]


DEFAULT_CONFIG_DIR = _project_root() / "config"


class GridSettings(BaseModel):
	"""Physical characteristics of the simulated warehouse grid."""

	width: PositiveInt = Field(20, description="Number of cells along the X axis.")
	height: PositiveInt = Field(15, description="Number of cells along the Y axis.")
	cell_size: PositiveInt = Field(40, description="Size of a grid cell in pixels (for UI).")


class TimingSettings(BaseModel):
	"""Timing configuration for the simulation loop and package generation."""

	update_interval_ms: PositiveInt = Field(150, description="UI/simulation update frequency.")
	package_spawn_rate_s: PositiveFloat = Field(3.0, description="Seconds between package spawns.")


class ColorSettings(BaseModel):
	"""Colour palette used by visual components."""

	grid: str = "#cccccc"
	background: str = "#ecf0f1"
	obstacle: str = "#7f8c8d"
	package: str = "#e67e22"
	path: str = "#3498db"
	dropoff: str = "#8e44ad"
	payload: str = "#c0392b"
	robots: Iterable[str] = Field(
		default=("#2980b9", "#c0392b", "#27ae60", "#f39c12", "#8e44ad"),
		description="Palette of robot colours (cycled as more robots are created).",
	)


class MQTTSettings(BaseModel):
	"""Messaging configuration for inter-robot coordination."""

	broker_host: str = Field(..., description="MQTT broker hostname or IP address.")
	port: PositiveInt = Field(1883, description="MQTT broker port.")
	topic_reservations: str = Field(
		"smart_warehouse/cell_reservations",
		description="Topic used for broadcasting cell reservations.",
	)
	username: Optional[str] = Field(None, description="Username for authenticated MQTT sessions.")
	password: Optional[str] = Field(None, description="Password for authenticated MQTT sessions.")
	use_tls: bool = Field(False, description="Enable TLS for MQTT connections.")
	ca_path: Optional[str] = Field(None, description="Path to CA certificate for TLS validation.")
	client_cert_path: Optional[str] = Field(None, description="Path to client certificate for mutual TLS.")
	client_key_path: Optional[str] = Field(None, description="Path to client private key for mutual TLS.")
	amqp_url: Optional[str] = Field(
		None,
		description="Optional AMQP URL to use when MQTT is unavailable.",
	)


class DatabaseSettings(BaseModel):
	"""Database configuration for persistence layers."""

	enabled: bool = Field(False, description="Enable persistent database usage.")
	url: AnyUrl = Field(
		"postgresql+asyncpg://warehouse:warehouse@localhost:5432/warehouse",
		description="SQLAlchemy-compatible database URL (async).",
	)
	pool_size: PositiveInt = Field(5, description="Connection pool size for the database engine.")
	max_overflow: PositiveInt = Field(10, description="Maximum overflow connections beyond pool size.")
	echo: bool = Field(False, description="Enable SQL echo for debugging.")


class TelemetrySettings(BaseModel):
	"""Tracing and metrics configuration."""

	otlp_endpoint: Optional[str] = Field(None, description="OTLP collector endpoint for traces.")
	metrics_enabled: bool = Field(True, description="Enable Prometheus metrics collection.")


class LoggingSettings(BaseModel):
	"""Logging verbosity and related tuning parameters."""

	level: str = Field("INFO", description="Root log level (DEBUG, INFO, etc.).")
	json: bool = Field(False, description="Emit logs as JSON for aggregators.")


def _load_yaml_file(path: Path) -> Dict[str, Any]:
	"""Safely load a YAML file into a dictionary.

	Parameters
	----------
	path:
		Path to the YAML file.

	Returns
	-------
	dict
		Parsed YAML content or an empty dict if the file does not exist.
	"""

	if not path.exists() or path.is_dir():
		return {}

	with path.open("r", encoding="utf-8") as handle:
		data = yaml.safe_load(handle)
		return data or {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
	"""Recursively merge ``override`` into ``base``.

	Nested dictionaries are merged rather than replaced, enabling granular
	overrides in environment-specific configuration files.
	"""

	result = base.copy()
	for key, value in override.items():
		if (
			key in result
			and isinstance(result[key], dict)
			and isinstance(value, dict)
		):
			result[key] = _deep_merge(result[key], value)
		else:
			result[key] = value
	return result


class AppSettings(BaseSettings):
	"""Primary configuration model for the application."""

	environment: str = Field("dev", description="Active environment name (dev, test, prod, ...).")
	grid: GridSettings = GridSettings()
	timing: TimingSettings = TimingSettings()
	colors: ColorSettings = ColorSettings()
	mqtt: MQTTSettings = MQTTSettings(broker_host="broker.hivemq.com")
	database: DatabaseSettings = DatabaseSettings()
	telemetry: TelemetrySettings = TelemetrySettings()
	logging: LoggingSettings = LoggingSettings()

	model_config = SettingsConfigDict(
		env_prefix="SW_",
		env_file=".env",
		env_file_encoding="utf-8",
		env_nested_delimiter="__",
		extra="ignore",
		validate_assignment=True,
	)

	@classmethod
	def _yaml_settings_source(cls) -> Dict[str, Any]:
		"""Produce settings from YAML configuration files."""

		config_dir = Path(os.getenv(_CONFIG_DIR_ENV_VAR, DEFAULT_CONFIG_DIR))
		base = _load_yaml_file(config_dir / "settings.yaml")
		env_name = os.getenv(_ENVIRONMENT_VAR, base.get("environment", "dev"))
		env_override = _load_yaml_file(config_dir / "environments" / f"{env_name}.yaml")

		merged = _deep_merge(base, env_override)
		merged.setdefault("environment", env_name)
		return merged

	@classmethod
	def settings_customise_sources(
		cls,
		_settings_cls,
		init_settings,
		env_settings,
		dotenv_settings,
		file_secret_settings,
	):
		"""Inject YAML files as the lowest-precedence settings source."""

		return (
			init_settings,
			env_settings,
			dotenv_settings,
			cls._yaml_settings_source,
			file_secret_settings,
		)


@lru_cache()
def get_settings(**overrides: Any) -> AppSettings:
	"""Return a cached :class:`AppSettings` instance.

	Keyword arguments are forwarded to :class:`AppSettings` and therefore have
	the highest precedence. The result is cached to avoid repeatedly parsing
	YAML files and environment variables.
	"""

	return AppSettings(**overrides)
