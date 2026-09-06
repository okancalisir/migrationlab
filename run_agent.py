"""Entry point: python run_agent.py INT-101."""

import argparse

from orchestrator.runner import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Migration Agent Lab")
    parser.add_argument("issue", help="Sample issue ID, for example INT-101")
    parser.add_argument("--source", choices=["sample", "jira"], default="sample")
    parser.add_argument("--service", default="", help="Source OSB service name")
    parser.add_argument("--analyze", action="store_true", help="Download sources and run the AI analysis")
    args = parser.parse_args()
    try:
        output = run(
            args.issue,
            source=args.source,
            service_name=args.service,
            perform_analysis=args.analyze,
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"[OK] Task loaded: {args.issue}")
    if args.analyze:
        print("[OK] Jira attachments downloaded and migration analysis completed.")
    else:
        print("[PENDING] Run with --analyze to execute the analysis agent.")
    print(f"[OK] Run status: {output}")


if __name__ == "__main__":
    main()
