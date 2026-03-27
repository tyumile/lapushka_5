from __future__ import annotations

import argparse
import sys

from app.reviewer import analyze_prompt, format_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Manual prompt reviewer. Works only with a prompt explicitly "
            "provided by the user in the current command."
        )
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Prompt text for manual review. If omitted, stdin is used.",
    )
    return parser


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt.strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    return ""


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    prompt_text = read_prompt(args)

    if not prompt_text:
        parser.print_help()
        print(
            "\nThis module does not scan prompts automatically. "
            "Pass a specific prompt directly."
        )
        return 1

    review = analyze_prompt(prompt_text)
    print(format_review(review))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
