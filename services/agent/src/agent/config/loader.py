"""Agent configuration loader and singleton."""

import json
import os
from pathlib import Path
from typing import Any, cast

import yaml

from agent._root import CONFIG_ROOT
from agent.src.exceptions import AppException, ErrorCodes
from agent.src.guardrails.config import GuardrailsConfig
from agent.src.settings import settings
from agent.src.token_budget.config import TokenBudgetConfig
from agent.utils.pylogger import get_python_logger

from .cache import CacheFileConfig
from .filesystem import FilesystemFileConfig
from .middleware import (
    MiddlewareFileConfig,
    PIIConfig,
    ResolvedMiddlewareConfig,
    resolve_middleware,
)
from .opa import OpaFileConfig
from .otel import OtelFileConfig
from .parser import parse_frontmatter
from .providers import ProvidersFileConfig
from .resolver import resolve_skill_paths, resolve_tools

logger = get_python_logger(log_level=settings.PYTHON_LOG_LEVEL)


def _config_text(path: Path) -> str:
    """A config file's contents, with any edit laid over it."""
    from agent.src.agent.config.resolution import effective_text

    return effective_text(path)


def _config_exists(path: Path) -> bool:
    """Whether a config file exists, counting one an edit created."""
    from agent.src.agent.config.resolution import effective_exists

    return effective_exists(path)


def _strip_jsonc_comments(text: str) -> str:
    """Remove ``//`` line comments outside JSON string literals."""
    result: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        if ch == '"':
            result.append(ch)
            i += 1
            while i < n:
                c = text[i]
                result.append(c)
                if c == "\\":
                    i += 1
                    if i < n:
                        result.append(text[i])
                elif c == '"':
                    break
                i += 1
            i += 1
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\n\r":
                i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _load_jsonc(path: Path) -> dict[str, Any]:
    """Load JSON with optional ``//`` line comments."""
    raw = _config_text(path)
    return cast(dict[str, Any], json.loads(_strip_jsonc_comments(raw)))


_AGENT_CONFIG_DIR = Path(
    os.getenv(
        "CONFIG_PATH",
        str(CONFIG_ROOT),
    )
)


def _section(model: Any, raw: dict[str, Any], name: str) -> Any:
    """One section of agent.yaml, or a refusal naming it."""
    try:
        return model.model_validate(raw.get(name) or {})
    except Exception as error:
        raise ConfigSectionUnreadable(
            f"'{name}' in runtime/agent.yaml could not be read: {error}. "
            "Leaving it out is how a deployment accepts the defaults; "
            "writing it and getting them anyway would reverse what it asked for."
        ) from error


class ConfigSectionUnreadable(RuntimeError):
    """A section of `agent.yaml` is written and cannot be read."""


class AgentConfigUnreadable(RuntimeError):
    """`agent.yaml` is present and will not parse."""


class ConfigVersionUnsupported(AgentConfigUnreadable):
    """The tree declares a version outside the window this build reads."""


class ExecutionConfigUnreadable(RuntimeError):
    """What a run may change is unknown."""


class PIIConfigUnreadable(RuntimeError):
    """`pii.yaml` is present and cannot be read, so scrubbing is unknown."""


class AgentConfig:
    """Singleton class for managing agent configuration operations."""

    _instance: "AgentConfig | None" = None
    _initialized: bool
    _configs_loaded: bool
    _base_dir: Path
    _orchestrator: dict[str, Any]
    _subagents: dict[str, dict[str, Any]]
    _mcp_servers: dict[str, Any]
    _available_skills: dict[str, Path]
    _middleware_config: MiddlewareFileConfig
    _filesystem_config: FilesystemFileConfig
    _providers_config: ProvidersFileConfig
    _cache_config: CacheFileConfig
    _opa_config: OpaFileConfig
    _otel_config: OtelFileConfig
    _token_budget_config: TokenBudgetConfig
    _guardrails_config: GuardrailsConfig
    _pii_config: PIIConfig
    _model_configs: dict[str, dict[str, Any]]
    _declared_schema_version: int | None
    _name: str

    def __new__(cls, base_dir: Path | None = None) -> "AgentConfig":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_dir: Path | None = None):
        """Initialize the AgentConfig singleton."""
        if self._initialized:
            return

        self._base_dir = base_dir if base_dir is not None else _AGENT_CONFIG_DIR
        self._initialized = True
        self._configs_loaded = False
        self._config_signature: tuple | None = None
        self._generation = 0
        self._declared_schema_version = None

    def _disk_signature(self) -> tuple:
        """Cheap fingerprint of everything `_ensure_loaded` reads."""
        root = self._base_dir
        if not root.is_dir():
            return (object(),)

        marks: list[tuple[str, float, int]] = []
        try:
            for path in sorted(root.rglob("*")):
                if path.is_dir() or path.name.startswith("."):
                    continue
                if path.suffix not in (".yaml", ".yml", ".json", ".md"):
                    continue
                stat = path.stat()
                marks.append((str(path), stat.st_mtime, stat.st_size))
        except OSError:
            return (object(),)
        from agent.src.agent.config.resolution import overlay_generation

        return (overlay_generation(), *marks)

    def _load_agent_yaml(self) -> dict[str, Any]:
        """Load the unified runtime/agent.yaml once."""
        agent_yaml = self._resolve("agent", "runtime/agent.yaml")
        if not _config_exists(agent_yaml):
            logger.warning("No runtime/agent.yaml found — using defaults")
            return {}

        try:
            text = _config_text(agent_yaml)
            from agent.src.agent.config.duplicate_keys import duplicate_keys
            from agent.src.agent.config.problems import note_problem

            for problem in duplicate_keys(text):
                logger.warning("runtime/agent.yaml: %s", problem)
                note_problem("runtime/agent.yaml", problem)

            raw = yaml.safe_load(text) or {}
        except Exception as error:
            raise AgentConfigUnreadable(
                f"{agent_yaml} could not be read: {error}. It holds how this "
                "agent is configured, so the agent will not start on defaults "
                "in its place."
            ) from error

        self._check_schema_version(raw)

        from agent.src.agent.config.deprecations import (
            deprecations_in,
            warn_once,
        )

        warn_once(deprecations_in(raw, self._base_dir))

        logger.info("Loaded runtime/agent.yaml")
        return raw

    def _check_schema_version(self, raw: dict[str, Any]) -> None:
        """Refuse a tree this build cannot read, and flag an old one."""
        from agent.src.agent.config.problems import note_problem
        from agent.src.agent.config.schema_version import (
            OLDEST_SUPPORTED,
            TooNew,
            TooOld,
            check_schema_version,
        )

        declared = raw.get("schema_version")
        if declared is not None and not isinstance(declared, int):
            raise ConfigVersionUnsupported(
                f"schema_version must be a whole number, not {declared!r}."
            )
        self._declared_schema_version = declared

        found = check_schema_version(declared)
        if isinstance(found, (TooOld, TooNew)):
            raise ConfigVersionUnsupported(found.message)

        if declared is None:
            note_problem(
                "runtime/agent.yaml",
                f"no schema_version — read as {OLDEST_SUPPORTED}, "
                "which will stop being supported",
            )
        elif found.deprecated:
            note_problem(
                "runtime/agent.yaml",
                f"schema_version {declared} is the oldest still supported",
            )

    def declared_schema_version(self) -> int | None:
        """The version the tree says it was written against."""
        self._ensure_loaded()
        return self._declared_schema_version

    def _load_guardrails_config(
        self, agent_yaml_guardrail: dict | None
    ) -> GuardrailsConfig:
        """Load guardrails configuration from the ``guardrail`` section of agent.yaml."""
        section = agent_yaml_guardrail or {}
        if not section.get("enabled", False):
            logger.info("Guardrail disabled in agent.yaml — skipping guardrail setup")
            return GuardrailsConfig(enabled=False)

        try:
            config: GuardrailsConfig = GuardrailsConfig.model_validate(section)
            logger.info(
                "Loaded guardrail config from agent.yaml (model=%s)", config.model
            )
            return config
        except Exception as e:
            logger.warning(
                "Failed to parse guardrail section — disabling guardrails: %s", e
            )
            return GuardrailsConfig(enabled=False)

    def _load_pii_config(self) -> PIIConfig:
        """Load PII configuration from runtime/pii.yaml."""
        pii_yaml = self._resolve("pii", "runtime/pii.yaml")
        if not _config_exists(pii_yaml):
            logger.info("No pii.yaml found — PII disabled")
            return PIIConfig()

        try:
            raw = yaml.safe_load(_config_text(pii_yaml)) or {}
            config: PIIConfig = PIIConfig.model_validate(raw)
        except Exception as error:
            raise PIIConfigUnreadable(
                f"{pii_yaml} could not be read: {error}. PII scrubbing is a "
                "privacy control, so the agent will not start without "
                "knowing what it should be doing. Fix the file, or write "
                "'enabled: false' to turn scrubbing off deliberately."
            ) from error

        logger.info("Loaded PII config from pii.yaml (enabled=%s)", config.enabled)
        return config

    def _load_otel_config(self) -> OtelFileConfig:
        """Load OpenTelemetry configuration from observability.yaml."""
        otel_yaml = self._resolve("observability", "runtime/observability.yaml")
        if not _config_exists(otel_yaml):
            logger.info("No observability.yaml found — OTEL disabled by default")
            return OtelFileConfig()

        try:
            raw = yaml.safe_load(_config_text(otel_yaml)) or {}
            config: OtelFileConfig = OtelFileConfig.model_validate(raw.get("otel", {}))
            logger.info("Loaded OTEL config from observability.yaml")
            return config
        except Exception as e:
            logger.warning("Failed to parse observability.yaml, using defaults: %s", e)
            return OtelFileConfig()

    def _ensure_loaded(self) -> None:
        """Lazy load configurations on first access."""
        if settings.CONFIG_AUTO_RELOAD and self._configs_loaded:
            signature = self._disk_signature()
            if signature != self._config_signature:
                logger.info("Config changed on disk — reloading")
                self._configs_loaded = False
            else:
                return

        if self._configs_loaded:
            return

        logger.info("Loading agent configurations...")

        raw = self._load_agent_yaml()

        self._middleware_config = MiddlewareFileConfig.model_validate(
            {
                "defaults": raw.get("middleware", {}),
                "profiles": raw.get("harness_profiles", {}),
            }
        )

        self._filesystem_config = FilesystemFileConfig.model_validate(
            raw.get("filesystem", {})
        )

        self._providers_config = ProvidersFileConfig.model_validate(
            {
                "resolve_strategy": raw.get("resolve_strategy", "legacy"),
                "providers": raw.get("providers", {}),
                "harness_profiles": raw.get("harness_profiles", {}),
                "async_tasks": raw.get("async_tasks", {}),
            }
        )

        self._opa_config = OpaFileConfig.model_validate(raw.get("opa", {}))

        self._cache_config = CacheFileConfig.model_validate(raw.get("cache", {}))

        self._otel_config = self._load_otel_config()

        self._guardrails_config = self._load_guardrails_config(raw.get("guardrail"))

        self._pii_config = self._load_pii_config()

        self._token_budget_config = TokenBudgetConfig.model_validate(
            raw.get("token_budget", {})
        )

        from agent.src.attachments.config import (
            AttachmentsConfig,
            ExtractionConfig,
        )

        self._attachments_config = _section(AttachmentsConfig, raw, "attachments")

        self._extraction_config = _section(ExtractionConfig, raw, "extraction")

        self._analytics_config: dict[str, Any] = dict(raw.get("analytics") or {})
        self._knowledge_raw: dict[str, Any] = dict(raw.get("knowledge") or {})
        self._limits_raw: dict[str, Any] = dict(raw.get("limits") or {})

        from agent.src.agent.config.middleware import ExecutionConfig

        written = raw.get("execution") or {}
        try:
            self._execution_config = ExecutionConfig.model_validate(written)
        except Exception as error:
            raise ExecutionConfigUnreadable(
                f"'execution' in runtime/agent.yaml could not be read: {written!r} "
                f"({error}). It decides whether a run may change anything, so "
                "the agent will not start without knowing. Use "
                "'effects: live' or 'effects: dry_run'."
            ) from error

        self._name = raw.get("name", "Agent")
        self._available_skills: dict[str, Path] = self._scan_available_skills()
        self._model_configs: dict[str, dict[str, Any]] = self._load_model_configs()
        self._orchestrator: dict[str, Any] = self._load_orchestrator()
        self._subagents: dict[str, dict[str, Any]] = self._load_all_subagents()
        self._mcp_servers: dict[str, Any] = self._load_mcp_servers()

        self._configs_loaded = True
        self._generation += 1
        self._config_signature = self._disk_signature()
        logger.info(
            f"Agent config loaded: orchestrator={self._orchestrator.get('name')}, "
            f"subagents={len(self._subagents)}, skills={len(self._available_skills)}"
        )

    def _resolve(self, name: str, fallback: str) -> Path:
        """Locate a config file, honouring legacy paths."""
        from agent.src.agent.config.paths import config_file, config_root

        if self._base_dir == config_root():
            resolved = config_file(name)
            if resolved is not None:
                return resolved
            return self._base_dir / fallback

        from agent.src.agent.config.paths import candidates_for

        try:
            options = candidates_for(name)
        except KeyError:
            options = ()
        for candidate in options:
            path = self._base_dir / candidate
            if path.exists():
                return path
        return self._base_dir / fallback

    @property
    def base_dir(self) -> Path:
        """Get the config base directory path."""
        return self._base_dir

    @staticmethod
    def _validate_string_list_field(value: Any, agent_name: str, *, field: str) -> None:
        """Validate a frontmatter field is a list of strings."""
        if not isinstance(value, list) or not all(isinstance(s, str) for s in value):
            raise AppException(
                f"Agent '{agent_name}': '{field}' must be a list of strings",
                ErrorCodes.CONFIGURATION_VALIDATION_ERROR,
            )

    def _load_orchestrator(self) -> dict[str, Any]:
        """Load orchestrator configuration at initialization."""
        orchestrator_path = self._resolve("prompt", "PROMPT.md")
        try:
            config = parse_frontmatter(orchestrator_path)

            agent_name = config.get("name", "orchestrator")
            if "mcps" in config:
                self._validate_string_list_field(
                    config["mcps"], agent_name, field="mcps"
                )
            if "resources" in config:
                self._validate_string_list_field(
                    config["resources"], agent_name, field="resources"
                )

            skill_names = config.get("skills", [])
            if skill_names:
                config["skill_paths"] = resolve_skill_paths(
                    skill_names,
                    self._available_skills,
                    agent_name=config.get("name", "orchestrator"),
                )

            return config
        except FileNotFoundError:
            raise AppException(
                f"Orchestrator config not found at {orchestrator_path}",
                ErrorCodes.CONFIGURATION_VALIDATION_ERROR,
            )
        except Exception as e:
            raise AppException(
                f"Failed to load orchestrator config: {e}",
                ErrorCodes.CONFIGURATION_VALIDATION_ERROR,
            )

    def _load_model_configs(self) -> dict[str, dict[str, Any]]:
        """Load model config YAML files from config/agent/models/."""
        models_dir = self._base_dir / "models"
        if not models_dir.is_dir():
            return {}

        configs: dict[str, dict[str, Any]] = {}
        for model_file in sorted(models_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(_config_text(model_file)) or {}
                if not isinstance(data, dict):
                    continue
                model_id = data.get("model_id", model_file.stem)

                raw_temp = data.get("temperature")
                if raw_temp is not None:
                    try:
                        data["temperature"] = float(raw_temp)
                    except (TypeError, ValueError):
                        logger.warning(
                            "Invalid temperature %r in %s, using default",
                            raw_temp,
                            model_file.name,
                        )
                        data.pop("temperature")

                raw_max = data.get("max_tokens")
                if raw_max is not None:
                    try:
                        data["max_tokens"] = int(float(raw_max))
                    except (TypeError, ValueError):
                        logger.warning(
                            "Invalid max_tokens %r in %s, using default",
                            raw_max,
                            model_file.name,
                        )
                        data.pop("max_tokens")

                configs[model_id] = data
                logger.info(
                    "Loaded model config: %s (provider=%s, temp=%s, max_tokens=%s)",
                    model_id,
                    data.get("provider", "?"),
                    data.get("temperature", "default"),
                    data.get("max_tokens", "default"),
                )
            except (yaml.YAMLError, OSError, ValueError) as e:
                logger.warning(
                    "Failed to parse model config %s: %s", model_file.name, e
                )

        return configs

    def _load_all_subagents(self) -> dict[str, dict[str, Any]]:
        """Load all subagent configurations at initialization."""
        subagents_dir = self._base_dir / "subagents"
        if not subagents_dir.is_dir():
            logger.warning(f"Subagents directory not found at {subagents_dir}")
            return {}

        subagents = {}
        for agent_file in sorted(subagents_dir.glob("*.md")):
            try:
                config = parse_frontmatter(agent_file)

                name = config.get("name", agent_file.stem)

                if "mcps" in config:
                    self._validate_string_list_field(config["mcps"], name, field="mcps")
                if "resources" in config:
                    self._validate_string_list_field(
                        config["resources"], name, field="resources"
                    )

                skill_names = config.get("skills", [])
                if skill_names:
                    config["skill_paths"] = resolve_skill_paths(
                        skill_names, self._available_skills, agent_name=name
                    )

                subagents[name] = config
                logger.info(f"Loaded subagent config: {name}")
            except Exception as e:
                logger.error(f"Failed to load subagent {agent_file}: {e}")

        return subagents

    @staticmethod
    def _validate_mcp_server(name: str, cfg: dict[str, Any]) -> None:
        """Log clear errors for invalid per-MCP OAuth/DCR configuration."""
        auth_mode = cfg.get("auth_mode", "sso")
        cfg["auth_mode"] = auth_mode

        if auth_mode not in ("sso", "oauth", "dcr", "api_key"):
            logger.error(
                "MCP server '%s': invalid auth_mode '%s' (expected sso, oauth, dcr, or api_key)",
                name,
                auth_mode,
            )
            return

        if auth_mode not in ("oauth", "dcr"):
            return

        oauth = cfg.get("oauth")
        if not isinstance(oauth, dict):
            if auth_mode == "dcr":
                logger.info(
                    "MCP server '%s': no oauth block — endpoints will be "
                    "discovered from the server's metadata on first connect",
                    name,
                )
            else:
                logger.error(
                    "MCP server '%s': auth_mode '%s' requires an 'oauth' block",
                    name,
                    auth_mode,
                )
            return

        grant_type = oauth.get("grant_type", "authorization_code")

        if auth_mode == "dcr" and grant_type == "client_credentials":
            logger.error(
                "MCP server '%s': auth_mode 'dcr' is incompatible with "
                "grant_type 'client_credentials' — use auth_mode 'oauth' instead",
                name,
            )
            return

        required_fields = ["token_endpoint"]
        if grant_type != "client_credentials":
            required_fields.append("authorization_endpoint")

        for field in required_fields:
            if not oauth.get(field):
                logger.error(
                    "MCP server '%s': oauth.%s is required for auth_mode '%s'",
                    name,
                    field,
                    auth_mode,
                )

        if oauth.get("redirect_uri"):
            logger.warning(
                "MCP server '%s': oauth.redirect_uri in mcp.json is ignored — "
                "redirect URI is derived from AGENT_PUBLIC_BASE_URL",
                name,
            )

        if auth_mode == "oauth" and not oauth.get("client_id"):
            logger.error(
                "MCP server '%s': oauth.client_id is required for auth_mode 'oauth'",
                name,
            )

        if oauth.get("client_secret"):
            logger.warning(
                "MCP server '%s': oauth.client_secret in mcp.json is insecure — "
                "use oauth.client_secret_env with an environment variable name instead",
                name,
            )

        if auth_mode == "dcr" and not oauth.get("registration_endpoint"):
            logger.error(
                "MCP server '%s': oauth.registration_endpoint is required for auth_mode 'dcr'",
                name,
            )

    def _load_mcp_servers(self) -> dict[str, Any]:
        """Load MCP server configuration at initialization."""
        mcp_path = self._resolve("mcp", "mcp.json")
        if not _config_exists(mcp_path):
            logger.warning(f"MCP config not found at {mcp_path}")
            return {}

        try:
            data = _load_jsonc(mcp_path)
            servers: dict[str, Any] = data.get("mcpServers", {})
            mock_url = os.environ.get("MCP_MOCK_URL", "").strip()

            for name, cfg in servers.items():
                if not isinstance(cfg, dict):
                    continue

                cfg.setdefault("enabled", True)
                cfg.setdefault("auth", True)
                cfg.setdefault("auth_mode", "dcr")

                if "transport" not in cfg and cfg.get("type"):
                    cfg["transport"] = (
                        "streamable_http" if cfg["type"] == "http" else cfg["type"]
                    )

                self._validate_mcp_server(name, cfg)

                if mock_url:
                    cfg["url"] = mock_url
                    cfg["auth"] = False

            if mock_url and servers:
                logger.warning(
                    "MCP_MOCK_URL is set: all %d server(s) point at %s and "
                    "authentication is off. This is the inner loop, not a "
                    "deployment.",
                    len(servers),
                    mock_url,
                )
            logger.info(f"Loaded {len(servers)} MCP server config(s)")
            return servers
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return {}

    def _scan_available_skills(self) -> dict[str, Path]:
        """Scan and index all available skills at initialization."""
        skills_dir = self._base_dir / "skills"
        if not skills_dir.is_dir():
            logger.warning(f"Skills directory not found at {skills_dir}")
            return {}

        skills = {}
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and not skill_path.name.startswith("."):
                skills[skill_path.name] = skill_path
                logger.debug(f"Found skill: {skill_path.name}")

        logger.info(f"Scanned {len(skills)} available skill(s)")
        return skills

    def get_orchestrator_config(self) -> dict[str, Any]:
        """Get the pre-loaded orchestrator configuration."""
        self._ensure_loaded()
        return self._orchestrator

    def get_model_params(self, model_id: str) -> dict[str, Any]:
        """Look up runtime LLM parameters for a model by model_id."""
        self._ensure_loaded()
        return self._model_configs.get(model_id, {})

    def get_available_skills(self) -> dict[str, Path]:
        """Every skill on disk, name to directory."""
        self._ensure_loaded()
        return self._available_skills

    def generation(self) -> int:
        """How many times the tree has been loaded in this process."""
        return self._generation

    def get_all_subagent_configs(self) -> dict[str, dict[str, Any]]:
        """Get all subagent configurations."""
        self._ensure_loaded()
        return self._subagents

    @staticmethod
    def resolve_tools(
        tool_names: list[str],
        available_tools: list[Any],
        agent_name: str = "agent",
    ) -> list[Any]:
        """Resolve tool names to actual tool objects."""
        return resolve_tools(tool_names, available_tools, agent_name)

    def get_mcp_servers(self) -> dict[str, Any]:
        """Get the pre-loaded MCP server configurations."""
        self._ensure_loaded()
        return self._mcp_servers

    def get_providers_config(self) -> ProvidersFileConfig:
        """Get the pre-loaded providers configuration."""
        self._ensure_loaded()
        return self._providers_config

    def get_filesystem_config(self) -> FilesystemFileConfig:
        """Get the pre-loaded filesystem configuration."""
        self._ensure_loaded()
        return self._filesystem_config

    def get_cache_config(self) -> CacheFileConfig:
        """Get the pre-loaded cache configuration."""
        self._ensure_loaded()
        return self._cache_config

    def get_opa_config(self) -> OpaFileConfig:
        """Get the pre-loaded OPA authorization configuration."""
        self._ensure_loaded()
        return self._opa_config

    def get_token_budget_config(self) -> TokenBudgetConfig:
        """Get the pre-loaded per-thread token budget configuration."""
        self._ensure_loaded()
        return self._token_budget_config

    def get_attachments_config(self) -> Any:
        """Attachment limits from agent.yaml, defaults when unset."""
        self._ensure_loaded()
        return self._attachments_config

    def get_extraction_config(self) -> Any:
        """Document-extraction engine from agent.yaml."""
        self._ensure_loaded()
        return self._extraction_config

    def get_analytics_config(self) -> dict[str, Any]:
        """The `analytics:` block from agent.yaml."""
        self._ensure_loaded()
        return self._analytics_config

    def get_limits_config(self) -> Any:
        """What one person, and one team, may spend in a day."""
        from agent.src.limits.config import read_limits

        self._ensure_loaded()
        return read_limits({"limits": self._limits_raw})

    def get_knowledge_config(self) -> Any:
        """Which document scopes this deployment keeps."""
        from agent.src.knowledge.config import read_knowledge

        self._ensure_loaded()
        return read_knowledge({"knowledge": self._knowledge_raw})

    def get_inbound_config(self) -> Any:
        """Whether another system may call this agent, and on what terms."""
        from agent.src.agent.config.inbound import Inbound, read_inbound

        path = self._resolve("mcp_server", "integrations/mcp_server.yaml")
        if not _config_exists(path):
            return Inbound()

        return read_inbound(yaml.safe_load(_config_text(path)) or {})

    def get_effects_mode(self) -> str:
        """Whether this deployment may actually change anything."""
        self._ensure_loaded()
        return str(self._execution_config.effects)

    def get_name(self) -> str:
        """Get the agent display name from config."""
        self._ensure_loaded()
        return self._name

    def get_custom_pii_config(self) -> PIIConfig:
        """Return the PII config loaded from pii.yaml."""
        self._ensure_loaded()
        return self._pii_config

    def get_middleware_config(self) -> MiddlewareFileConfig:
        """Get the pre-loaded middleware file configuration."""
        self._ensure_loaded()
        return self._middleware_config

    def resolve_agent_middleware(
        self,
        model_name: str,
        agent_overrides: dict[str, Any] | None = None,
    ) -> ResolvedMiddlewareConfig:
        """Resolve middleware config for a specific agent."""
        self._ensure_loaded()
        return resolve_middleware(self._middleware_config, model_name, agent_overrides)

    def get_otel_config(self) -> OtelFileConfig:
        """Get the pre-loaded OTEL configuration."""
        self._ensure_loaded()
        return self._otel_config

    def get_guardrails_config(self) -> GuardrailsConfig:
        """Get the pre-loaded guardrails configuration."""
        self._ensure_loaded()
        return self._guardrails_config

    def get_pyproject_path(self) -> Path:
        """Get the skill sandbox pyproject.toml path."""
        return self._base_dir / "skills" / "pyproject.toml"


agent_config = AgentConfig(_AGENT_CONFIG_DIR)
