"""Initial local workflow. AI and tools will be added step by step."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.analysis_agent import analyze, write_outputs
from orchestrator.jira import JiraClient, load_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(issue: str, source: str = "sample", service_name: str = "",
        perform_analysis: bool = False) -> Path:
    if not re.fullmatch(r"[A-Z][A-Z0-9]*-[0-9]+", issue):
        raise ValueError("Expected an issue ID such as INT-101.")

    if source == "jira":
        settings = load_settings(PROJECT_ROOT)
        jira = JiraClient(settings)
        raw = jira.get_issue(issue)
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
    jira_dir = output_dir / "jira"
    jira_dir.mkdir(parents=True, exist_ok=True)
    (jira_dir / "task.json").write_text(
        json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest: list[dict] = []
    generated_outputs: dict[str, str] = {}
    analysis_metadata: dict = {}
    selected_service = service_name.strip()
    status_name = "TASK_LOADED"
    if perform_analysis:
        if source != "jira":
            attachment_dir = PROJECT_ROOT / "samples" / issue / "attachments"
            manifest = [
                {
                    "id": path.name,
                    "originalName": path.name,
                    "storedName": path.name,
                    "mimeType": "text/plain",
                    "size": path.stat().st_size,
                }
                for path in sorted(attachment_dir.iterdir())
                if path.is_file() and path.name != "README.md"
            ]
            settings = load_settings(PROJECT_ROOT)
        else:
            attachment_dir = jira_dir / "attachments"
            manifest = jira.download_attachments(task.get("attachments", []), attachment_dir)
        selected_service = selected_service or str(task.get("title") or "").strip()
        if not selected_service:
            raise ValueError("Provide the source service name with --service.")
        result, analysis_metadata = analyze(
            task, selected_service, attachment_dir, manifest, settings
        )
        paths = write_outputs(result, analysis_metadata, output_dir)
        generated_outputs = {name: str(path) for name, path in paths.items()}
        status_name = "ANALYSIS_COMPLETED"
    (jira_dir / "attachment-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    output = output_dir / "run-status.json"
    status = {
        "issue": issue,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": status_name,
        "source": source,
        "serviceName": selected_service,
        "aiAnalysisPerformed": perform_analysis,
        "downloadedAttachments": manifest,
        "analysisMetadata": analysis_metadata,
        "outputs": generated_outputs,
        "nextStep": (
            "Review analysis and resolve missing information before code generation."
            if perform_analysis else
            "Run again with --analyze and --service after adding Jira attachments."
        ),
        "task": task,
    }
    output.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output
