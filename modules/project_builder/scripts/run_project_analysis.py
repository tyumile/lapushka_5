#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from app.ai_client import ProjectAnalysisAIClient
from app.config import load_config
from app.doc_classifier_source import DocClassifierReader
from app.project_analysis import ProjectAnalysisError, ProjectAnalysisRunner
from app.registry_source import IngestRegistryReader
from db.repository import ProjectBuilderRepository
from db.setup import initialize_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a project document against ingest_registry files.")
    parser.add_argument("--project-document-id", type=int, required=True, help="file_registry.id of the project document")
    parser.add_argument("--cabinet-id", default="default", help="Cabinet context for ingest_registry and project analysis")
    parser.add_argument(
        "--project-file-path",
        type=Path,
        help="Optional local path to the project file if ingest_registry stores only remote metadata.",
    )
    parser.add_argument(
        "--source-id",
        dest="source_ids",
        action="append",
        type=int,
        default=[],
        help="Limit candidate documents to a specific source_id. Repeatable.",
    )
    parser.add_argument(
        "--document-id",
        dest="document_ids",
        action="append",
        type=int,
        default=[],
        help="Limit candidate documents to specific file_registry ids. Repeatable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call the external agent. Save only request context and a stub result file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    initialize_database(config.db_path)
    repository = ProjectBuilderRepository(config.db_path)
    reader = IngestRegistryReader(config.ingest_registry_db_path, config.ingest_registry_base_dir)
    doc_classifier_reader = DocClassifierReader(config.doc_classifier_db_path)
    ai_client = ProjectAnalysisAIClient(
        api_key=config.openai_api_key,
        model=config.openai_model,
        timeout_seconds=config.openai_timeout_seconds,
    )
    runner = ProjectAnalysisRunner(config, repository, reader, ai_client, doc_classifier_reader)
    try:
        result = runner.run(
            project_document_id=args.project_document_id,
            cabinet_id=args.cabinet_id,
            source_ids=args.source_ids or None,
            document_ids=args.document_ids or None,
            project_file_path=args.project_file_path,
            dry_run=args.dry_run,
        )
    except ProjectAnalysisError as error:
        print(f"error={error}", file=sys.stderr)
        return 1

    print(f"status=ok run_dir={result.run_dir}")
    print(f"request_context={result.request_context_path}")
    print(f"result_json={result.result_path}")
    print(
        "project_document_id="
        f"{result.project_document.id} candidate_documents={result.candidate_documents_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
