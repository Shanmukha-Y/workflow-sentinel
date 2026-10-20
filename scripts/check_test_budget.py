"""Enforce the collected unittest budget without filtering discovery.

This catches common collection shortcuts, not semantic bundling: reviewers must still
keep one input scenario per test. Iteration over one result's records is not a new case.
"""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 50


def main():
    declared = 0
    for path in sorted((ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "load_tests":
                    raise SystemExit(f"Custom discovery is not allowed: {path}")
                if node.name.startswith("test_"):
                    declared += 1
                    if node.decorator_list:
                        raise SystemExit(f"Test decorators need explicit case accounting: {path}")
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
                if name in {"subTest", "skipTest", "parametrize", "parameterize"}:
                    raise SystemExit(f"Variants/skips need explicit collected cases: {path}")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test*.py")
    count = suite.countTestCases()
    if unittest.defaultTestLoader.errors:
        raise SystemExit("Test discovery failed")
    if count != declared or not 0 < count <= LIMIT:
        raise SystemExit(
            f"Test budget failed: {count} collected, {declared} declared, limit {LIMIT}"
        )
    print(f"Test budget passed: {count}/{LIMIT} collected cases (no filtered discovery)")


if __name__ == "__main__":
    main()
