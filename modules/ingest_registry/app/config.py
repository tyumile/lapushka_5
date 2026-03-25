import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    module_name: str
    host: str
    port: int
    base_dir: Path
    data_dir: Path
    storage_dir: Path
    upload_dir: Path
    bootstrap_dir: Path
    db_path: Path
    log_path: Path


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    storage_dir = data_dir / "storage"
    upload_dir = storage_dir / "uploads"
    bootstrap_dir = storage_dir / "bootstrap"
    host = os.getenv("INGEST_REGISTRY_HOST", "0.0.0.0")
    port = int(os.getenv("INGEST_REGISTRY_PORT", "8101"))
    return Settings(
        module_name="ingest_registry",
        host=host,
        port=port,
        base_dir=base_dir,
        data_dir=data_dir,
        storage_dir=storage_dir,
        upload_dir=upload_dir,
        bootstrap_dir=bootstrap_dir,
        db_path=data_dir / "ingest_registry.sqlite3",
        log_path=base_dir / "logs" / "ingest_registry.log",
    )
