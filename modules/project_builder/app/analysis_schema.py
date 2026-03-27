from copy import deepcopy
from typing import Any


RESULT_TEMPLATE: dict[str, Any] = {
    "project": {
        "project_document_id": "",
        "project_file_name": "",
        "project_file_path": "",
        "project_code": "",
        "project_name": "",
        "analysis_summary": "",
        "analysis_notes": "",
    },
    "modules": [],
    "unmatched_documents": [],
    "analysis_warnings": [],
}


def schema_for_prompt() -> dict[str, Any]:
    return deepcopy(
        {
            "project": {
                "project_document_id": "string_or_number",
                "project_file_name": "string",
                "project_file_path": "string",
                "project_code": "string",
                "project_name": "string",
                "analysis_summary": "string",
                "analysis_notes": "string",
            },
            "modules": [
                {
                    "module_id": "string",
                    "module_name": "string",
                    "module_type": "building|section|floor|discipline|mixed|other",
                    "building": "string",
                    "section": "string",
                    "floor": "string",
                    "discipline": "string",
                    "source_reference": {
                        "page": "string",
                        "sheet": "string",
                        "quote": "string",
                    },
                    "materials": [
                        {
                            "material_name": "string",
                            "document_name": "string",
                            "document_number": "string",
                            "document_date": "string",
                            "project_source": {
                                "page": "string",
                                "sheet": "string",
                                "quote": "string",
                            },
                            "document_disk_path": "string",
                            "document_registry_id": "string_or_number",
                            "document_source_title": "string",
                            "document_source_url": "string",
                            "match_reason": "string",
                        }
                    ],
                    "norms": [
                        {
                            "norm_name": "string",
                            "project_source": {
                                "page": "string",
                                "sheet": "string",
                                "quote": "string",
                            },
                        }
                    ],
                }
            ],
            "unmatched_documents": [
                {
                    "document_registry_id": "string_or_number",
                    "document_name": "string",
                    "document_disk_path": "string",
                    "reason": "string",
                }
            ],
            "analysis_warnings": ["string"],
        }
    )


def normalize_analysis_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(RESULT_TEMPLATE)
    project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    result["project"] = {
        "project_document_id": _to_string(project.get("project_document_id")),
        "project_file_name": _to_string(project.get("project_file_name")),
        "project_file_path": _to_string(project.get("project_file_path")),
        "project_code": _to_string(project.get("project_code")),
        "project_name": _to_string(project.get("project_name")),
        "analysis_summary": _to_string(project.get("analysis_summary")),
        "analysis_notes": _to_string(project.get("analysis_notes")),
    }
    result["modules"] = [_normalize_module(item) for item in _as_list(payload.get("modules"))]
    result["unmatched_documents"] = [
        {
            "document_registry_id": _to_string(item.get("document_registry_id")),
            "document_name": _to_string(item.get("document_name")),
            "document_disk_path": _to_string(item.get("document_disk_path")),
            "reason": _to_string(item.get("reason")),
        }
        for item in _as_list(payload.get("unmatched_documents"))
        if isinstance(item, dict)
    ]
    result["analysis_warnings"] = [_to_string(item) for item in _as_list(payload.get("analysis_warnings")) if _to_string(item)]
    return result


def _normalize_module(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    return {
        "module_id": _to_string(item.get("module_id")),
        "module_name": _to_string(item.get("module_name")),
        "module_type": _to_string(item.get("module_type")),
        "building": _to_string(item.get("building")),
        "section": _to_string(item.get("section")),
        "floor": _to_string(item.get("floor")),
        "discipline": _to_string(item.get("discipline")),
        "source_reference": _normalize_reference(item.get("source_reference")),
        "materials": [_normalize_material(material) for material in _as_list(item.get("materials"))],
        "norms": [_normalize_norm(norm) for norm in _as_list(item.get("norms"))],
    }


def _normalize_material(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    return {
        "material_name": _to_string(item.get("material_name")),
        "document_name": _to_string(item.get("document_name")),
        "document_number": _to_string(item.get("document_number")),
        "document_date": _to_string(item.get("document_date")),
        "project_source": _normalize_reference(item.get("project_source")),
        "document_disk_path": _to_string(item.get("document_disk_path")),
        "document_registry_id": _to_string(item.get("document_registry_id")),
        "document_source_title": _to_string(item.get("document_source_title")),
        "document_source_url": _to_string(item.get("document_source_url")),
        "match_reason": _to_string(item.get("match_reason")),
    }


def _normalize_norm(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    return {
        "norm_name": _to_string(item.get("norm_name")),
        "project_source": _normalize_reference(item.get("project_source")),
    }


def _normalize_reference(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        item = {}
    return {
        "page": _to_string(item.get("page")),
        "sheet": _to_string(item.get("sheet")),
        "quote": _to_string(item.get("quote")),
    }


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _to_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
