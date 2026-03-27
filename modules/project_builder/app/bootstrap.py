import logging

from app.ai_client import ProjectAnalysisAIClient
from app.analysis_store import AnalysisStore
from app.config import load_config
from app.doc_classifier_source import DocClassifierReader
from app.project_analysis import ProjectAnalysisRunner
from app.registry_source import IngestRegistryReader
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
    registry_reader = IngestRegistryReader(config.ingest_registry_db_path, config.ingest_registry_base_dir)
    doc_classifier_reader = DocClassifierReader(config.doc_classifier_db_path)
    ai_client = ProjectAnalysisAIClient(
        api_key=config.openai_api_key,
        model=config.openai_model,
        timeout_seconds=config.openai_timeout_seconds,
    )
    analysis_runner = ProjectAnalysisRunner(
        config=config,
        repository=repository,
        registry_reader=registry_reader,
        ai_client=ai_client,
        doc_classifier_reader=doc_classifier_reader,
    )
    service = ProjectBuilderService(
        repository,
        AnalysisStore(config.analysis_dir),
        registry_reader=registry_reader,
        analysis_runner=analysis_runner,
    )
    logging.getLogger(__name__).info(
        "Starting %s on http://%s:%s",
        config.module_name,
        config.host,
        config.port,
    )
    run_server(config.host, config.port, service)
