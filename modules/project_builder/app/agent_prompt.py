import json
from pathlib import Path


def load_prompt(prompt_path: Path, schema_path: Path) -> str:
    prompt_template = prompt_path.read_text(encoding="utf-8")
    schema_text = schema_path.read_text(encoding="utf-8")
    return prompt_template.format(output_schema=schema_text)


def render_context_block(project_document: dict[str, object], candidate_documents: list[dict[str, object]]) -> str:
    payload = {
        "project_document": project_document,
        "candidate_documents": candidate_documents,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
