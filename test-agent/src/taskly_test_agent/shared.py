"""Data shared with the Claude Code alternative, from agent-shared/ at the repo root.

Only data lives there (skills, instructions, the report schema, skip rules);
each engine has its own code that reads it.
"""

import json
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[3] / "agent-shared"

INSTRUCTIONS = (SHARED_DIR / "instructions.md").read_text().strip()
REPORT_SCHEMA = json.loads((SHARED_DIR / "report.schema.json").read_text())
SKIP_RULES = json.loads((SHARED_DIR / "skip-rules.json").read_text())
