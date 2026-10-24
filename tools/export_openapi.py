"""Write the API's OpenAPI schema to frontend/openapi.json; the frontend's types are generated from it.

Run after changing the API: uv run python tools/export_openapi.py, then cd frontend && npm run generate
(CI checks that both are up to date).
"""

import json

from helpdesk.api.app import app
from helpdesk.core.paths import ROOT

OUTPUT = ROOT / "frontend" / "openapi.json"

if __name__ == "__main__":
    schema = json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True)
    OUTPUT.write_text(schema + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(app.openapi()['paths'])} paths)")
