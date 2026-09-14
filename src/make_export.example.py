#!/usr/bin/env python3
"""Fill your own ids into the generated workflow so it can be imported into n8n.

    python3 build_workflow.py        -> workflow/job-scanner.workflow.json   (committed, no secrets)
    python3 make_export.example.py   -> workflow/job-scanner.local.json      (git-ignored, yours)

Keeping these as two steps means the committed workflow can never drift from the
generator, and the file carrying your sheet id never reaches git.
"""
import json, pathlib

HERE = pathlib.Path(__file__).parent
SHEET_ID = "PASTE_GOOGLE_SHEET_ID_HERE"
CREDS = {                       # ids come from your own n8n credential list
    "googleSheetsOAuth2Api": {"id": "REPLACE_ME", "name": "Google Sheets account"},
    "gmailOAuth2":           {"id": "REPLACE_ME", "name": "Gmail account"},
    "anthropicApi":          {"id": "REPLACE_ME", "name": "Anthropic account"},
}

wf = json.loads((HERE.parent / "workflow" / "job-scanner.workflow.json").read_text())
for n in wf["nodes"]:
    for a in n.get("parameters", {}).get("assignments", {}).get("assignments", []):
        if a.get("name") == "sheet_id":
            a["value"] = SHEET_ID
    for key in list(n.get("credentials", {})):
        if key in CREDS:
            n["credentials"][key] = dict(CREDS[key])

out = HERE.parent / "workflow" / "job-scanner.local.json"
out.write_text(json.dumps(wf, indent=2, ensure_ascii=False))
print(f"wrote {out} ({len(wf['nodes'])} nodes) - do not commit this file")
