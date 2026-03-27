import logging
import threading

from app.ai_client import OpenAIClassifierClient
from app.config import load_config
from app.pipeline import DocumentProcessor
from app.registry_source import IngestRegistryReader
from app.service import DocumentService
from app.source_fetcher import SourceFileFetcher
from db.repository import DocumentRepository
from db.setup import initialize_database
from ui.server import build_server


def bootstrap_and_run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    config = load_config()
    initialize_database(config.db_path)
    config.temp_dir.mkdir(parents=True, exist_ok=True)
    repository = DocumentRepository(config.db_path)
    registry_reader = IngestRegistryReader(
        db_path=config.ingest_registry_db_path,
        base_dir=config.ingest_registry_base_dir,
    )
    processor = DocumentProcessor(
        ai_client=OpenAIClassifierClient(
            api_key=config.openai_api_key,
            model=config.openai_model,
            timeout_seconds=config.openai_timeout_seconds,
            max_units_per_request=config.openai_max_units_per_request,
            max_input_chars_per_request=config.openai_max_input_chars_per_request,
        ),
        temp_dir=config.temp_dir,
        pdf_chunk_size_bytes=config.pdf_chunk_size_bytes,
    )
    service = DocumentService(
        repository,
        registry_reader,
        processor,
        SourceFileFetcher(config.temp_dir / "downloads"),
    )
    server = build_server(config.host, config.port, service)
    repository.add_module_event(
        event_type="module_start",
        details="doc_classifier started with AI-based working documentation processing",
    )
    threading.Thread(target=service.bootstrap, daemon=True).start()
    logging.getLogger(__name__).info(
        "Starting %s on http://%s:%s",
        config.module_name,
        config.host,
        config.port,
    )
    server.serve_forever()
