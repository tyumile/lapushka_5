from app.reviewer import build_default_policy


def main() -> None:
    policy = build_default_policy()
    print(policy.to_text())


if __name__ == "__main__":
    main()
