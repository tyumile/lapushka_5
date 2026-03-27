import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    module_name: str
    host: str
    port: int
    base_dir: Path
    data_dir: Path
    db_path: Path
    ingest_registry_db_path: Path
    ingest_registry_base_dir: Path
    openai_api_key: str
    openai_model: str
    openai_timeout_seconds: int
    openai_max_units_per_request: int
    openai_max_input_chars_per_request: int
    pdf_chunk_size_bytes: int
    temp_dir: Path


def load_config() -> AppConfig:
    base_dir = Path(__file__).resolve().parent.parent
    project_root = base_dir.parents[1]
    data_dir = base_dir / "data"
    return AppConfig(
        module_name="doc_classifier",
        host=os.getenv("DOC_CLASSIFIER_HOST", "0.0.0.0"),
        port=int(os.getenv("DOC_CLASSIFIER_PORT", "8002")),
        base_dir=base_dir,
        data_dir=data_dir,
        db_path=data_dir / "doc_classifier.sqlite3",
        ingest_registry_db_path=project_root / "modules" / "ingest_registry" / "data" / "ingest_registry.sqlite3",
        ingest_registry_base_dir=project_root / "modules" / "ingest_registry",
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        openai_timeout_seconds=int(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")),
        openai_max_units_per_request=int(os.getenv("OPENAI_MAX_UNITS_PER_REQUEST", "12")),
        openai_max_input_chars_per_request=int(os.getenv("OPENAI_MAX_INPUT_CHARS_PER_REQUEST", "18000")),
        pdf_chunk_size_bytes=10 * 1024 * 1024,
        temp_dir=data_dir / "tmp",
    )
