from pathlib import Path

import yaml


root = Path(__file__).resolve().parents[2]
workflow = root / ".github" / "workflows" / "ci.yml"
data = yaml.safe_load(workflow.read_text(encoding="utf-8"))

if not isinstance(data, dict) or "jobs" not in data:
    raise SystemExit("Workflow YAML does not define jobs")
if "pull_request" not in data.get(True, data.get("on", {})):
    raise SystemExit("Workflow YAML does not define pull_request")
if "workflow_dispatch" not in data.get(True, data.get("on", {})):
    raise SystemExit("Workflow YAML does not define workflow_dispatch")
print(f"Workflow YAML: OK ({len(data['jobs'])} jobs)")
