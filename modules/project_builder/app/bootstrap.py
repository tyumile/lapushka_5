import logging

from app.config import load_config
from app.service import ProjectBuilderService
from db.repository import ProjectBuilderRepository
from db.setup import initialize_database
from ui.server import run_server


def bootstrap_and_run() -> None:
    config = load_config()
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(config.log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    initialize_database(config.db_path)
    repository = ProjectBuilderRepository(config.db_path)
    repository.seed_demo_data()
    repository.add_module_event(
        event_type="module_start",
        details="project_builder started with local HTTP UI and seeded demo data",
    )
    repository.add_task_registry_entry(
        task_id="project_builder-bootstrap",
        source_agent="codex",
        target_agent="project_builder",
        module_name=config.module_name,
        action_type="bootstrap",
        summary="Initial module scaffold, UI, database and demo project data prepared",
        status="done",
        artifacts="main.py,app/,db/,ui/,data/project_builder.sqlite3,README.md",
    )
    service = ProjectBuilderService(repository)
    logging.getLogger(__name__).info(
        "Starting %s on http://%s:%s",
        config.module_name,
        config.host,
        config.port,
    )
    run_server(config.host, config.port, service)
