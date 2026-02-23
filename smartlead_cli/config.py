"""Configuration management for smartlead-cli."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import tomlkit

CONFIG_PATH = Path.home() / ".config" / "smartlead-cli" / "config.toml"
DEFAULT_BASE_URL = "https://server.smartlead.ai/api/v1"


@dataclass
class Config:
    api_key: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 30.0
    retries: int = 3
    default_limit: int = 100
    pretty: bool = False


def load_config(
    api_key_flag: Optional[str] = None,
    base_url_flag: Optional[str] = None,
) -> Config:
    """Load config with priority: file < env < CLI flags."""
    cfg = Config()

    if CONFIG_PATH.exists():
        try:
            doc = tomlkit.parse(CONFIG_PATH.read_text())
            core = doc.get("core", {})
            defaults = doc.get("defaults", {})
            if core.get("api_key"):
                cfg.api_key = str(core["api_key"])
            if core.get("base_url"):
                cfg.base_url = str(core["base_url"])
            if core.get("timeout_seconds") is not None:
                cfg.timeout_seconds = float(core["timeout_seconds"])
            if core.get("retries") is not None:
                cfg.retries = int(core["retries"])
            if defaults.get("limit") is not None:
                cfg.default_limit = int(defaults["limit"])
        except Exception:
            pass

    if os.environ.get("SMARTLEAD_API_KEY"):
        cfg.api_key = os.environ["SMARTLEAD_API_KEY"]
    if os.environ.get("SMARTLEAD_BASE_URL"):
        cfg.base_url = os.environ["SMARTLEAD_BASE_URL"]

    if api_key_flag is not None:
        cfg.api_key = api_key_flag
    if base_url_flag is not None:
        cfg.base_url = base_url_flag

    if cfg.timeout_seconds <= 0:
        cfg.timeout_seconds = 30.0
    if cfg.retries < 1:
        cfg.retries = 1
    if cfg.default_limit < 1:
        cfg.default_limit = 100

    return cfg


def save_config(cfg: Config) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        doc = tomlkit.parse(CONFIG_PATH.read_text())
    else:
        doc = tomlkit.document()

    if "core" not in doc:
        doc["core"] = tomlkit.table()
    if "defaults" not in doc:
        doc["defaults"] = tomlkit.table()

    if cfg.api_key:
        doc["core"]["api_key"] = cfg.api_key
    elif "api_key" in doc["core"]:
        del doc["core"]["api_key"]

    doc["core"]["base_url"] = cfg.base_url
    doc["core"]["timeout_seconds"] = float(cfg.timeout_seconds)
    doc["core"]["retries"] = int(cfg.retries)
    doc["defaults"]["limit"] = int(cfg.default_limit)

    CONFIG_PATH.write_text(tomlkit.dumps(doc))


def save_config_key(dotted_key: str, value: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        doc = tomlkit.parse(CONFIG_PATH.read_text())
    else:
        doc = tomlkit.document()

    parts = dotted_key.split(".", 1)
    if len(parts) == 2:
        section, key = parts
        if section not in doc:
            doc[section] = tomlkit.table()
        doc[section][key] = _coerce_scalar(value)
    else:
        doc[dotted_key] = _coerce_scalar(value)

    CONFIG_PATH.write_text(tomlkit.dumps(doc))


def config_as_dict(cfg: Config, reveal: bool = False) -> dict[str, Any]:
    api_key = cfg.api_key
    if api_key and not reveal:
        visible = api_key[:8] if len(api_key) >= 8 else api_key
        api_key = f"{visible}...{'*' * 8}"

    return {
        "core": {
            "api_key": api_key,
            "base_url": cfg.base_url,
            "timeout_seconds": cfg.timeout_seconds,
            "retries": cfg.retries,
        },
        "defaults": {
            "limit": cfg.default_limit,
        },
    }


def _coerce_scalar(value: str) -> Any:
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null":
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
