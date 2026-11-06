"""Print the in-scope endpoint list for a security test, from the API contract committed in the repository.

Usage: python3 scripts/security-scope.py BASE_URL [BASE_URL ...]
The contract is openapi.json at the repository root, or the OpenAPI file named by API_CONTRACT (JSON, or YAML when
PyYAML is installed).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

METHODS = ("get", "post", "put", "patch", "delete")


def load_contract(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        import yaml  # only YAML contracts need PyYAML

        return yaml.safe_load(text)
    return json.loads(text)


def main(bases: list[str]) -> int:
    if not bases:
        print(__doc__, file=sys.stderr)
        return 2
    contract = Path(os.environ.get("API_CONTRACT", Path(__file__).resolve().parent.parent / "openapi.json"))
    if not contract.is_file():
        print(f"no API contract at {contract}: commit the OpenAPI file or set API_CONTRACT", file=sys.stderr)
        return 1
    paths = load_contract(contract).get("paths", {})
    if not paths:
        print(f"{contract} lists no paths; the scope would be empty", file=sys.stderr)
        return 1
    print("| Base URL | Method | Path |")
    print("|---|---|---|")
    for base in bases:
        for path in sorted(paths):
            for method in METHODS:
                if method in paths[path]:
                    print(f"| {base.rstrip('/')} | {method.upper()} | {path} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
