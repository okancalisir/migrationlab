"""Entry point: python run_agent.py INT-101."""

import argparse

from orchestrator.runner import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Migration Agent Lab")
    parser.add_argument("issue", help="Sample issue ID, for example INT-101")
    parser.add_argument("--source", choices=["sample", "jira"], default="sample")
    args = parser.parse_args()
    try:
        output = run(args.issue, source=args.source)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"[OK] Task loaded: {args.issue}")
    print("[PENDING] AI integration has not been configured yet.")
    print(f"[OK] Run status: {output}")


if __name__ == "__main__":
    main()
