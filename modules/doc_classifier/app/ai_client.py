import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


TYPE_CATALOG = {
    "quality_document": {
        "label": "Документ качества",
        "fields": [
            ("material_name", "Название материала"),
            ("document_name", "Название документа"),
            ("document_number", "Номер документа"),
            ("issue_date", "Дата выдачи"),
            ("certifying_body", "Сертифицирующий орган"),
            ("applicant_or_manufacturer", "Заявитель или производитель"),
            ("manufacturer", "Производитель"),
            ("batch_or_lot", "Партия"),
            ("quantity_or_volume", "Объем"),
            ("standard_reference", "Нормативный документ"),
        ],
    },
    "project_document": {
        "label": "Проект",
        "fields": [
            ("project_code", "Шифр проекта"),
            ("project_name", "Название проекта"),
            ("document_name", "Название документа"),
            ("document_number", "Номер документа"),
            ("document_date", "Дата документа"),
            ("city", "Город"),
            ("object_name", "Объект"),
            ("developer", "Заказчик"),
            ("designer", "Проектировщик"),
            ("chief_engineer", "ГИП"),
            ("chief_architect", "Главный архитектор"),
            ("building_count", "Количество корпусов"),
            ("section_count", "Количество секций"),
            ("floor_count", "Количество этажей"),
            ("stage", "Стадия"),
        ],
    },
    "estimate_document": {
        "label": "Смета",
        "fields": [
            ("estimate_type", "Тип сметы"),
            ("estimate_code", "Шифр сметы"),
            ("project_code", "Шифр проекта"),
            ("object_name", "Объект"),
            ("document_date", "Дата документа"),
            ("compiler", "Составитель"),
            ("total_cost", "Итоговая стоимость"),
            ("labor_cost", "Трудозатраты"),
            ("material_cost", "Стоимость материалов"),
            ("equipment_cost", "Стоимость оборудования"),
            ("overheads", "Накладные расходы"),
            ("profit", "Сметная прибыль"),
        ],
    },
    "order_document": {
        "label": "Приказ",
        "fields": [
            ("order_number", "Номер приказа"),
            ("order_date", "Дата приказа"),
            ("organization", "Организация"),
            ("appointment_title", "На какую должность"),
            ("person_name", "Фамилия И.О."),
            ("basis", "Основание"),
            ("object_name", "Объект"),
        ],
    },
    "work_log": {
        "label": "Журнал работ",
        "fields": [
            ("journal_name", "Название журнала"),
            ("journal_number", "Номер журнала"),
            ("start_date", "Дата начала"),
            ("end_date", "Дата окончания"),
            ("organization", "Организация"),
            ("object_name", "Объект"),
            ("responsible_person", "Ответственное лицо"),
        ],
    },
    "act_document": {
        "label": "Акт",
        "fields": [
            ("act_name", "Название акта"),
            ("act_number", "Номер акта"),
            ("act_date", "Дата акта"),
            ("object_name", "Объект"),
            ("work_type", "Вид работ"),
            ("participants", "Участники"),
            ("related_materials", "Связанные материалы"),
        ],
    },
    "as_built_scheme": {
        "label": "Исполнительная схема",
        "fields": [
            ("scheme_name", "Название схемы"),
            ("scheme_number", "Номер схемы"),
            ("document_date", "Дата документа"),
            ("object_name", "Объект"),
            ("work_scope", "Объем работ"),
            ("location", "Участок"),
            ("responsible_person", "Ответственное лицо"),
        ],
    },
    "test_report": {
        "label": "Протокол/отчет испытаний",
        "fields": [
            ("report_name", "Название протокола"),
            ("report_number", "Номер"),
            ("report_date", "Дата"),
            ("laboratory", "Лаборатория"),
            ("material_name", "Материал или конструкция"),
            ("test_method", "Метод испытаний"),
            ("result", "Результат"),
        ],
    },
    "permit_document": {
        "label": "Разрешительный документ",
        "fields": [
            ("document_name", "Название документа"),
            ("document_number", "Номер документа"),
            ("document_date", "Дата"),
            ("issuing_authority", "Выдавший орган"),
            ("organization", "Организация"),
            ("object_name", "Объект"),
            ("valid_until", "Срок действия"),
        ],
    },
    "other_working_document": {
        "label": "Прочая рабочая документация",
        "fields": [
            ("document_name", "Название документа"),
            ("document_number", "Номер документа"),
            ("document_date", "Дата документа"),
            ("organization", "Организация"),
            ("object_name", "Объект"),
            ("summary", "Краткое содержание"),
        ],
    },
}


@dataclass(frozen=True)
class AIExtractionResult:
    document_type: str
    document_type_label: str
    summary: str
    confidence: float
    reasoning: str
    fields: list[dict[str, str]]
    executive_doc_targets: list[str]
    recognized_text: str
    notes: str
    raw_response: dict[str, Any]


class OpenAIClassifierClient:
    responses_url = "https://api.openai.com/v1/responses"
    files_url = "https://api.openai.com/v1/files"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_units_per_request: int,
        max_input_chars_per_request: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_units_per_request = max_units_per_request
        self.max_input_chars_per_request = max_input_chars_per_request
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
            }
        )

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def classify_text_document(self, metadata: dict[str, Any], text: str) -> AIExtractionResult:
        input_items = [
            {
                "type": "input_text",
                "text": self._metadata_block(metadata) + "\n\nТекст документа:\n" + text,
            }
        ]
        payload = self._create_payload(input_items)
        response_payload = self._post_response(payload)
        return self._normalize_result(response_payload, text)

    def classify_file_document(
        self,
        metadata: dict[str, Any],
        file_paths: list[Path],
        text_hint: str = "",
    ) -> AIExtractionResult:
        uploaded_ids = [self._upload_file(path) for path in file_paths[: self.max_units_per_request]]
        input_items: list[dict[str, Any]] = [
            {"type": "input_text", "text": self._metadata_block(metadata, text_hint)}
        ]
        for file_id in uploaded_ids:
            input_items.append({"type": "input_file", "file_id": file_id})
        payload = self._create_payload(input_items)
        response_payload = self._post_response(payload)
        return self._normalize_result(response_payload, text_hint)

    def classify_image_document(self, metadata: dict[str, Any], image_path: Path) -> AIExtractionResult:
        return self.classify_image_document_batch(metadata, [image_path])

    def classify_image_document_batch(
        self,
        metadata: dict[str, Any],
        image_paths: list[Path],
    ) -> AIExtractionResult:
        input_items = [{"type": "input_text", "text": self._metadata_block(metadata)}]
        for image_path in image_paths[: self.max_units_per_request]:
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".bmp": "image/bmp",
                ".webp": "image/webp",
            }.get(image_path.suffix.lower(), "image/jpeg")
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            input_items.append({"type": "input_image", "image_url": f"data:{mime_type};base64,{encoded}"})
        payload = self._create_payload(input_items)
        response_payload = self._post_response(payload)
        return self._normalize_result(response_payload, "")

    def _create_payload(self, input_items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": self._system_prompt()}],
                },
                {"role": "user", "content": input_items},
            ],
        }

    def _post_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            self.responses_url,
            json=payload,
            timeout=(10, self.timeout_seconds),
        )
        response.raise_for_status()
        return response.json()

    def _upload_file(self, path: Path) -> str:
        with path.open("rb") as handle:
            response = self.session.post(
                self.files_url,
                data={"purpose": "user_data"},
                files={"file": (path.name, handle, "application/octet-stream")},
                timeout=(10, self.timeout_seconds),
            )
        response.raise_for_status()
        payload = response.json()
        return str(payload["id"])

    def _normalize_result(self, response_payload: dict[str, Any], recognized_text: str) -> AIExtractionResult:
        content_text = _extract_text_output(response_payload)
        parsed = json.loads(content_text)
        document_type = parsed.get("document_type") or "other_working_document"
        catalog_entry = TYPE_CATALOG.get(document_type, TYPE_CATALOG["other_working_document"])
        fields = _normalize_fields(parsed.get("fields"), catalog_entry["fields"])
        return AIExtractionResult(
            document_type=document_type,
            document_type_label=str(parsed.get("document_type_label") or catalog_entry["label"]),
            summary=str(parsed.get("summary") or ""),
            confidence=float(parsed.get("confidence") or 0.0),
            reasoning=str(parsed.get("reasoning") or ""),
            fields=fields,
            executive_doc_targets=[
                str(item).strip()
                for item in parsed.get("executive_doc_targets", [])
                if str(item).strip()
            ],
            recognized_text=str(parsed.get("recognized_text") or recognized_text or ""),
            notes=str(parsed.get("notes") or ""),
            raw_response=parsed,
        )

    def _metadata_block(self, metadata: dict[str, Any], text_hint: str = "") -> str:
        payload = {
            "file_name": metadata.get("file_name", ""),
            "file_path": metadata.get("file_path", ""),
            "file_size": metadata.get("file_size", 0),
            "page_count": metadata.get("page_count", 0),
            "text_hint_present": bool(text_hint),
        }
        block = "Метаданные документа:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
        if text_hint:
            return block + "\n\nЛокально извлеченный текст/фрагмент:\n" + text_hint
        return block

    def _system_prompt(self) -> str:
        return (
            "Ты анализируешь строительный документ для последующего формирования исполнительной документации. "
            "Работай только по данным из входного файла, изображения, metadata и локально извлеченного текста. "
            "Ничего не додумывай. "
            "Если реквизит явно не найден, верни пустую строку. "
            "Если локально извлеченный текст присутствует, считай его главным источником фактов. "
            "Имя файла используй только как слабую подсказку, когда в документе нет читаемого содержимого. "
            "Верни строго один JSON-объект без markdown и без пояснений. "
            "Допустимые document_type: "
            + ", ".join(TYPE_CATALOG.keys())
            + ". "
            "JSON-поля верхнего уровня: document_type, document_type_label, summary, confidence, reasoning, "
            "recognized_text, notes, executive_doc_targets, fields. "
            "fields должен быть массивом объектов {name,label,value}. "
            "Используй только допустимые name для выбранного document_type и не добавляй новые поля. "
            "Для quality_document допустимы только: material_name, document_name, document_number, issue_date, "
            "certifying_body, applicant_or_manufacturer, manufacturer, batch_or_lot, quantity_or_volume, standard_reference. "
            "Для project_document допустимы только: project_code, project_name, document_name, document_number, "
            "document_date, city, object_name, developer, designer, chief_engineer, chief_architect, "
            "building_count, section_count, floor_count, stage. "
            "Для estimate_document допустимы только: estimate_type, estimate_code, project_code, object_name, "
            "document_date, compiler, total_cost, labor_cost, material_cost, equipment_cost, overheads, profit. "
            "Для order_document допустимы только: order_number, order_date, organization, appointment_title, "
            "person_name, basis, object_name. "
            "Для work_log допустимы только: journal_name, journal_number, start_date, end_date, organization, "
            "object_name, responsible_person. "
            "Для act_document допустимы только: act_name, act_number, act_date, object_name, work_type, participants, related_materials. "
            "Для as_built_scheme допустимы только: scheme_name, scheme_number, document_date, object_name, work_scope, location, responsible_person. "
            "Для test_report допустимы только: report_name, report_number, report_date, laboratory, material_name, test_method, result. "
            "Для permit_document допустимы только: document_name, document_number, document_date, issuing_authority, organization, object_name, valid_until. "
            "Для other_working_document допустимы только: document_name, document_number, document_date, organization, object_name, summary. "
            "Для каждого найденного ключевого реквизита заполняй value только точным значением из документа. "
            "Не переименовывай поля и не добавляй новые поля. "
            "Если в тексте есть номер, дата, орган сертификации, заявитель, производитель, название продукции "
            "или нормативный документ, ты обязан извлечь их в соответствующие поля. "
            "Если в тексте есть название типа документа, например Сертификат соответствия, Декларация о соответствии "
            "или Проектная документация, заполни document_name этим типом, а не именем файла. "
            "confidence: 0.9-1.0 только если тип документа и ключевые реквизиты подтверждены текстом; "
            "0.6-0.89 если тип понятен, но часть реквизитов отсутствует; "
            "0.0-0.59 если вывод в основном основан на имени файла или слабых признаках. "
            "reasoning должен кратко объяснять, на каких фразах документа основан выбор типа. "
            "notes должен явно сказать, использовался ли fallback по имени файла."
        )


def _extract_text_output(response_payload: dict[str, Any]) -> str:
    if response_payload.get("output_text"):
        return str(response_payload["output_text"])
    output = response_payload.get("output") or []
    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    raise ValueError("OpenAI response does not contain text output")


def _normalize_fields(
    payload: Any,
    defaults: list[tuple[str, str]],
) -> list[dict[str, str]]:
    by_name: dict[str, dict[str, str]] = {}
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            label = str(item.get("label") or name).strip()
            value = str(item.get("value") or "").strip()
            if name:
                by_name[name] = {"name": name, "label": label, "value": value}
    result: list[dict[str, str]] = []
    for name, label in defaults:
        current = by_name.get(name, {"name": name, "label": label, "value": ""})
        result.append(current)
    return result
