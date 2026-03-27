from dataclasses import dataclass


IMPORTANT_FINDINGS = (
    "broken_foreign_keys",
    "duplicate_rows_in_key_entities",
    "empty_critical_fields",
    "unclear_table_or_column_names",
    "status_or_id_storage_conflicts",
)


@dataclass(frozen=True)
class ReviewerScope:
    module_name: str
    purpose: str
    restrictions: tuple[str, ...]


SCOPE = ReviewerScope(
    module_name="db_reviewer",
    purpose="Проверка БД модулей-процессников на чистоту, целостность и понятность структуры.",
    restrictions=(
        "Не изменяет чужие БД напрямую.",
        "Не запускает миграции без отдельного указания.",
        "Не исправляет данные вручную.",
    ),
)


def build_reviewer_overview() -> str:
    important_findings = ", ".join(IMPORTANT_FINDINGS)
    restrictions = "\n".join(f"- {item}" for item in SCOPE.restrictions)
    return (
        f"{SCOPE.module_name}\n"
        f"Роль: {SCOPE.purpose}\n"
        "Важные замечания: "
        f"{important_findings}\n"
        "Ограничения:\n"
        f"{restrictions}"
    )
