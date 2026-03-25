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


def load_config() -> AppConfig:
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    return AppConfig(
        module_name="doc_classifier",
        host=os.getenv("DOC_CLASSIFIER_HOST", "0.0.0.0"),
        port=int(os.getenv("DOC_CLASSIFIER_PORT", "8102")),
        base_dir=base_dir,
        data_dir=data_dir,
        db_path=data_dir / "doc_classifier.sqlite3",
    )
