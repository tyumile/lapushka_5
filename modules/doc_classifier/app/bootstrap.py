import logging

from app.config import load_config
from app.service import DocumentService
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
    repository = DocumentRepository(config.db_path)
    repository.seed_demo_documents()
    service = DocumentService(repository)
    server = build_server(config.host, config.port, service)
    repository.add_module_event(
        event_type="module_start",
        details="doc_classifier started with local HTTP UI",
    )
    logging.getLogger(__name__).info(
        "Starting %s on http://%s:%s",
        config.module_name,
        config.host,
        config.port,
    )
    server.serve_forever()
