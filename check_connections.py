"""Check GitHub remote access and/or authenticated Jira access."""

import argparse
import subprocess
from pathlib import Path

from orchestrator.jira import JiraClient, load_settings

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["github", "jira", "all"])
    args = parser.parse_args()
    failed = False
    if args.service in ("github", "all"):
        try:
            result = subprocess.run(
                ["git", "ls-remote", "origin"], cwd=ROOT,
                capture_output=True, text=True, timeout=45,
            )
            if result.returncode:
                raise ValueError("Check origin, network access and Git credentials.")
            print("[OK] GitHub remote is readable. This does not verify push permission.")
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            print(f"[FAIL] GitHub: {exc}")
            failed = True
    if args.service in ("jira", "all"):
        try:
            JiraClient(load_settings(ROOT)).check_connection()
            print("[OK] Jira authenticated connection verified.")
        except (OSError, ValueError) as exc:
            print(f"[FAIL] Jira: {exc}")
            failed = True
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
