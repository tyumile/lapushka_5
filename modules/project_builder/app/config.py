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
    logs_dir: Path
    db_path: Path
    log_path: Path


def load_config() -> AppConfig:
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    logs_dir = base_dir / "logs"
    return AppConfig(
        module_name="project_builder",
        host=os.getenv("PROJECT_BUILDER_HOST", "0.0.0.0"),
        port=int(os.getenv("PROJECT_BUILDER_PORT", "8103")),
        base_dir=base_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        db_path=data_dir / "project_builder.sqlite3",
        log_path=logs_dir / "project_builder.log",
    )
