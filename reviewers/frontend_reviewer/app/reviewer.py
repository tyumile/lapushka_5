from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewPolicy:
    title: str
    checks: tuple[str, ...]
    limits: tuple[str, ...]
    upload_fixture_dir: str

    def to_text(self) -> str:
        lines = [self.title, "", "Base checks:"]
        lines.extend(f"- {item}" for item in self.checks)
        lines.append("")
        lines.append("Limits:")
        lines.extend(f"- {item}" for item in self.limits)
        lines.append("")
        lines.append(f"Upload fixtures: {self.upload_fixture_dir}")
        return "\n".join(lines)


def build_default_policy() -> ReviewPolicy:
    return ReviewPolicy(
        title="frontend_reviewer: lightweight browser smoke checks",
        checks=(
            "Open the target page and confirm it renders.",
            "Verify the main interactive element is visible.",
            "Run one short button or form interaction.",
            "Confirm the UI shows a result or a readable error.",
            "Confirm all user-facing texts are in Russian.",
        ),
        limits=(
            "Use headless mode only.",
            "Do not record video.",
            "Do not run long or repeated scenarios.",
            "Use only small local files for upload checks.",
        ),
        upload_fixture_dir="tests/fixtures/",
    )
