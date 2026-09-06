"""Initial local workflow. AI and tools will be added step by step."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.jira import JiraClient, load_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(issue: str, source: str = "sample") -> Path:
    if not re.fullmatch(r"[A-Z][A-Z0-9]*-[0-9]+", issue):
        raise ValueError("Expected an issue ID such as INT-101.")

    if source == "jira":
        raw = JiraClient(load_settings(PROJECT_ROOT)).get_issue(issue)
        fields = raw.get("fields", {})
        task = {
            "issue": raw.get("key"),
            "title": fields.get("summary"),
            "description": fields.get("description"),
            "attachments": fields.get("attachment", []),
        }
    elif source == "sample":
        task_path = PROJECT_ROOT / "samples" / issue / "task.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
    else:
        raise ValueError("Source must be sample or jira.")
    if not isinstance(task, dict) or task.get("issue") != issue:
        raise ValueError("Task file must contain the matching issue ID.")

    output_dir = PROJECT_ROOT / "workspace" / issue
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "run-status.json"
    status = {
        "issue": issue,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "TASK_LOADED",
        "source": source,
        "aiAnalysisPerformed": False,
        "nextStep": "Add OSB sample files and configure the model integration.",
        "task": task,
    }
    output.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output
