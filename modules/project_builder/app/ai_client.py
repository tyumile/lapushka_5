import json
from pathlib import Path
from typing import Any

import requests


class ProjectAnalysisAIClient:
    responses_url = "https://api.openai.com/v1/responses"
    files_url = "https://api.openai.com/v1/files"

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def analyze_project(
        self,
        prompt_text: str,
        context_text: str,
        project_file_path: Path,
    ) -> dict[str, Any]:
        uploaded_file_id = self._upload_file(project_file_path)
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": prompt_text}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Контекст задачи:\n" + context_text},
                        {"type": "input_file", "file_id": uploaded_file_id},
                    ],
                },
            ],
        }
        response = self.session.post(
            self.responses_url,
            json=payload,
            timeout=(10, self.timeout_seconds),
        )
        _raise_for_status_with_body(response)
        response_payload = response.json()
        return json.loads(_extract_text_output(response_payload))

    def analyze_project_text(
        self,
        prompt_text: str,
        context_text: str,
        project_text: str,
        project_file_name: str,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": prompt_text}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Контекст задачи:\n"
                                + context_text
                                + "\n\nТекст проекта из файла "
                                + project_file_name
                                + ":\n"
                                + project_text
                            ),
                        }
                    ],
                },
            ],
        }
        response = self.session.post(
            self.responses_url,
            json=payload,
            timeout=(10, self.timeout_seconds),
        )
        _raise_for_status_with_body(response)
        response_payload = response.json()
        return json.loads(_extract_text_output(response_payload))

    def _upload_file(self, path: Path) -> str:
        with path.open("rb") as handle:
            response = self.session.post(
                self.files_url,
                data={"purpose": "user_data"},
                files={"file": (path.name, handle, "application/octet-stream")},
                timeout=(10, self.timeout_seconds),
            )
        _raise_for_status_with_body(response)
        payload = response.json()
        return str(payload["id"])


def _extract_text_output(response_payload: dict[str, Any]) -> str:
    if response_payload.get("output_text"):
        return str(response_payload["output_text"])
    for item in response_payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    raise ValueError("OpenAI response does not contain text output")


def _raise_for_status_with_body(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        body = response.text.strip()
        if body:
            raise requests.HTTPError(f"{error}. Response body: {body}", response=response) from error
        raise
