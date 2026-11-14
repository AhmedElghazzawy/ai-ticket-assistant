"""The layer rules of ARCHITECTURE.md, checked on every import, so they cannot drift silently.

core <- domain <- ai, storage <- retrieval <- services <- api, evals: a layer imports only the layers
below it. api/app.py and api/deps.py are the "composition root": they build the real Gemini client,
pool and search index and hand them to the use cases, so they may import any layer.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parent.parent / "src" / "helpdesk"

ALLOWED: dict[str, set[str]] = {
    "core": set(),
    "domain": {"core"},
    "ai": {"core", "domain"},
    "storage": {"core", "domain"},
    "retrieval": {"core", "domain", "ai", "storage"},
    "services": {"core", "domain", "ai", "storage", "retrieval"},
    "api": {"core", "domain", "services"},
    "evals": {"core", "domain", "ai", "storage", "retrieval", "services"},
}
COMPOSITION_ROOT = {"api/app.py", "api/deps.py"}


def layer_imports(path: Path) -> set[str]:
    """The helpdesk layers this file imports (`helpdesk.<layer>...`)."""
    layers = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names = []
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        for name in names:
            parts = name.split(".")
            if parts[0] == "helpdesk" and len(parts) > 1 and parts[1] in ALLOWED:
                layers.add(parts[1])
    return layers


MODULES = sorted(p for p in PACKAGE.rglob("*.py") if p.parent != PACKAGE)


def test_every_module_belongs_to_a_known_layer() -> None:
    assert {p.relative_to(PACKAGE).parts[0] for p in MODULES} == set(ALLOWED)
    assert [p.name for p in PACKAGE.glob("*.py")] == ["__init__.py"]  # no loose modules on top


@pytest.mark.parametrize("path", MODULES, ids=lambda p: str(p.relative_to(PACKAGE)))
def test_a_layer_imports_only_the_layers_below_it(path: Path) -> None:
    relative = path.relative_to(PACKAGE)
    layer = relative.parts[0]
    if relative.as_posix() in COMPOSITION_ROOT:
        return
    wrong = layer_imports(path) - ALLOWED[layer] - {layer}
    assert not wrong, f"{relative} ({layer}) must not import {sorted(wrong)}"
