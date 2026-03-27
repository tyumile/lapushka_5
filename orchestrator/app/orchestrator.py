from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestratorProfile:
    module_name: str
    role: str
    boundaries: tuple[str, ...]
    responsibilities: tuple[str, ...]
    action_types: tuple[str, ...]
    statuses: tuple[str, ...]

    def render_summary(self) -> str:
        lines = [
            f"module={self.module_name}",
            f"role={self.role}",
            "responsibilities:",
        ]
        lines.extend(f"- {item}" for item in self.responsibilities)
        lines.append("action_types:")
        lines.extend(f"- {item}" for item in self.action_types)
        lines.append("statuses:")
        lines.extend(f"- {item}" for item in self.statuses)
        lines.append("boundaries:")
        lines.extend(f"- {item}" for item in self.boundaries)
        return "\n".join(lines)
