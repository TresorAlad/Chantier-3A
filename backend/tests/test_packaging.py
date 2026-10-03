"""Verifie que l image Docker / setuptools incluent les modules racine du CLI."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _pyproject_py_modules() -> set[str]:
    text = (BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("py-modules"):
            _, rhs = line.split("=", 1)
            inner = rhs.strip().strip("[]")
            return {part.strip().strip('"').strip("'") for part in inner.split(",") if part.strip()}
    raise AssertionError("py-modules introuvable dans pyproject.toml")


def _dockerfile_copied_py_modules() -> set[str]:
    copied: set[str] = set()
    for line in (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("COPY ") or ".py" not in line:
            continue
        for token in line.split():
            if token.endswith(".py"):
                copied.add(token.replace(".py", ""))
    return copied


def test_py_modules_exist_on_disk():
    for name in _pyproject_py_modules():
        path = BACKEND_ROOT / f"{name}.py"
        assert path.is_file(), f"module manquant: {path}"


def test_dockerfile_copies_all_py_modules():
    modules = _pyproject_py_modules()
    copied = _dockerfile_copied_py_modules()
    missing = modules - copied
    assert not missing, f"Dockerfile ne copie pas: {sorted(missing)}"


def test_cli_imports_without_side_effects():
    ast.parse((BACKEND_ROOT / "cli.py").read_text(encoding="utf-8"))
