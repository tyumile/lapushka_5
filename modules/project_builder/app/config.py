import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    module_name: str
    host: str
    port: int
    base_dir: Path
    project_root: Path
    data_dir: Path
    logs_dir: Path
    db_path: Path
    log_path: Path
    prompts_dir: Path
    analysis_dir: Path
    ingest_registry_db_path: Path
    ingest_registry_base_dir: Path
    doc_classifier_db_path: Path
    openai_api_key: str
    openai_model: str
    openai_timeout_seconds: int
    openai_max_input_chars_per_request: int


def _load_root_env(project_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env_path = project_root / ".env"
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def load_config() -> AppConfig:
    base_dir = Path(__file__).resolve().parent.parent
    project_root = base_dir.parents[1]
    env = _load_root_env(project_root)
    data_dir = base_dir / "data"
    logs_dir = base_dir / "logs"
    return AppConfig(
        module_name="project_builder",
        host=env.get("PROJECT_BUILDER_HOST", "0.0.0.0"),
        port=int(env.get("PROJECT_BUILDER_PORT", "8003")),
        base_dir=base_dir,
        project_root=project_root,
        data_dir=data_dir,
        logs_dir=logs_dir,
        db_path=data_dir / "project_builder.sqlite3",
        log_path=logs_dir / "project_builder.log",
        prompts_dir=base_dir / "prompts",
        analysis_dir=data_dir / "project_analyses",
        ingest_registry_db_path=project_root / "modules" / "ingest_registry" / "data" / "ingest_registry.sqlite3",
        ingest_registry_base_dir=project_root / "modules" / "ingest_registry",
        doc_classifier_db_path=project_root / "modules" / "doc_classifier" / "data" / "doc_classifier.sqlite3",
        openai_api_key=env.get("OPENAI_API_KEY", "").strip(),
        openai_model=env.get("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        openai_timeout_seconds=int(env.get("OPENAI_TIMEOUT_SECONDS", "120")),
        openai_max_input_chars_per_request=int(env.get("OPENAI_MAX_INPUT_CHARS_PER_REQUEST", "18000")),
    )
