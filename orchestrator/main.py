from app.bootstrap import create_orchestrator


def main() -> None:
    orchestrator = create_orchestrator()
    print(orchestrator.render_summary())


if __name__ == "__main__":
    main()
