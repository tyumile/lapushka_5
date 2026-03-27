from app.orchestrator import OrchestratorProfile
from app.statuses import TASK_ACTION_TYPES, TASK_STATUSES


def create_orchestrator() -> OrchestratorProfile:
    return OrchestratorProfile(
        module_name="orchestrator",
        role="Routes tasks between modules and reviewers, tracks statuses, and records handoff boundaries.",
        responsibilities=(
            "Read task state from the shared SQL registry before routing work.",
            "Create handoff records that point work to the next target agent.",
            "Keep module coordination separate from shell UI and business modules.",
        ),
        boundaries=(
            "Does not implement business logic for process modules.",
            "Does not store other modules' domain data locally.",
            "Does not provide shell frontend behavior from this module.",
        ),
        action_types=TASK_ACTION_TYPES,
        statuses=TASK_STATUSES,
    )
