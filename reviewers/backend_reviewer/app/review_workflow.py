from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewerModuleInfo:
    module_name: str
    module_root: Path
    review_templates_dir: Path
    report_templates_dir: Path


def build_module_info(base_dir: Path) -> ReviewerModuleInfo:
    """Return paths used by the reviewer module."""
    return ReviewerModuleInfo(
        module_name="backend_reviewer",
        module_root=base_dir,
        review_templates_dir=base_dir / "prompts" / "recommendations",
        report_templates_dir=base_dir / "prompts" / "reports",
    )


def render_startup_message(info: ReviewerModuleInfo) -> str:
    """Keep the entrypoint explicit and easy to verify."""
    return (
        f"{info.module_name} ready\n"
        f"- module_root: {info.module_root}\n"
        f"- recommendation_templates: {info.review_templates_dir}\n"
        f"- report_templates: {info.report_templates_dir}\n"
        "- role: review completed backend modules without editing them"
    )
