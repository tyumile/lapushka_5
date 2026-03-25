import logging
from http.server import ThreadingHTTPServer

from app.config import load_settings
from app.service import IngestRegistryService
from db.repository import RegistryRepository
from ui.http import IngestRegistryHandler


def configure_logging(log_path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_server() -> ThreadingHTTPServer:
    settings = load_settings()
    configure_logging(settings.log_path)
    repository = RegistryRepository(settings.db_path)
    service = IngestRegistryService(settings, repository)
    service.bootstrap()

    handler = IngestRegistryHandler.build(service)
    server = ThreadingHTTPServer((settings.host, settings.port), handler)
    logging.getLogger(__name__).info(
        "Module started on http://%s:%s", settings.host, settings.port
    )
    return server
