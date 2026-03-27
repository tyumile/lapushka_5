from pathlib import Path

from app.review_workflow import build_module_info, render_startup_message


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    module_info = build_module_info(base_dir)
    print(render_startup_message(module_info))


if __name__ == "__main__":
    main()
