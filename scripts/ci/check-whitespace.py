import os
import subprocess
from pathlib import Path


root = Path(__file__).resolve().parents[2]
base_ref = os.getenv("GITHUB_BASE_REF", "").strip()
if base_ref:
    revision = f"origin/{base_ref}...HEAD"
    command = ["git", "-C", str(root), "diff", "--check", revision]
else:
    command = ["git", "-C", str(root), "show", "--check", "--format=", "HEAD"]

result = subprocess.run(command, text=True)
if result.returncode:
    raise SystemExit(result.returncode)
print(f"Changed-file whitespace check: OK ({revision if base_ref else 'HEAD'})")
