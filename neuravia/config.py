from __future__ import annotations
from dataclasses import dataclass, field, fields
from pathlib import Path
import tomllib, os

PROFILES = ["safe", "balanced", "danger"]
OS_MODES = ["auto", "windows", "linux"]

@dataclass
class General:
    profile: str = "safe"
    os_mode: str = "auto"
    dry_run: bool = False
    no_confirm: bool = False
    sandbox_path: str = "data/sandbox"
    log_dir: str = "data/logs"
    kill_switch_path: str = "data/kill.switch"

@dataclass
class Security:
    chain_secret: str = ""
    # nouvelle option supportée par config/profiles/*.toml
    shell_allowlist: list[str] = field(default_factory=lambda: ["echo"])

@dataclass
class Network:
    enabled: bool = False
    # d'autres clés (ex: allowed_domains, http_timeout_sec) peuvent exister dans les TOML,
    # elles seront ignorées proprement par le filtre.

@dataclass
class Modules:
    filesystem: bool = True
    process: bool = True
    http: bool = False
    browser: bool = False
    vision: bool = False
    ocr: bool = False
    codeedit: bool = True

@dataclass
class LLM:
    local_enabled: bool = True
    remote_enabled: bool = False

@dataclass
class Memory:
    db_path: str = "data/memory.db"
    index_enabled: bool = False

@dataclass
class Settings:
    general: General
    security: Security
    network: Network
    modules: Modules
    llm: LLM
    memory: Memory

def _load_toml_if_exists(path: Path) -> dict:
    if path.exists():
        with path.open("rb") as f:
            return tomllib.load(f)
    return {}

def _read_profile_toml(config_path: Path, profile: str) -> dict:
    """
    Cherche dans:
      - config/defaults.toml et config/<profile>.toml
      - puis fallback: config/profiles/defaults.toml et config/profiles/<profile>.toml
    """
    cfg_dir = config_path if config_path.is_dir() else config_path.parent

    data = _load_toml_if_exists(cfg_dir / "defaults.toml")
    if not data:
        data = _load_toml_if_exists(cfg_dir / "profiles" / "defaults.toml")

    prof = _load_toml_if_exists(cfg_dir / f"{profile}.toml")
    if not prof:
        prof = _load_toml_if_exists(cfg_dir / "profiles" / f"{profile}.toml")

    # Fusion superficielle defaults <- profil
    base = data or {}
    for k, v in prof.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return base

def _filter_for_dataclass(cls, data: dict) -> dict:
    """Ne garde que les clés connues du dataclass (évite TypeError sur clés en trop)."""
    allowed = {f.name for f in fields(cls)}
    return {k: v for k, v in (data or {}).items() if k in allowed}

def load_settings(config: str | None, profile: str, overrides: dict | None = None) -> Settings:
    config_path = Path(config) if config else Path("config")
    raw = _read_profile_toml(config_path, profile)

    # Secret HMAC via env prioritaire
    if "security" not in raw:
        raw["security"] = {}
    env_secret = os.environ.get("NEURAVIA_CHAIN_SECRET")
    if env_secret:
        raw["security"]["chain_secret"] = env_secret

    g = General(**_filter_for_dataclass(General, raw.get("general")))
    s = Security(**_filter_for_dataclass(Security, raw.get("security")))
    n = Network(**_filter_for_dataclass(Network, raw.get("network")))
    m = Modules(**_filter_for_dataclass(Modules, raw.get("modules")))
    l = LLM(**_filter_for_dataclass(LLM, raw.get("llm")))
    mem = Memory(**_filter_for_dataclass(Memory, raw.get("memory")))

    # Overrides (seulement sur General pour l’instant)
    if overrides:
        for k, v in overrides.items():
            if hasattr(g, k):
                setattr(g, k, v)

    return Settings(general=g, security=s, network=n, modules=m, llm=l, memory=mem)
