import re
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "skypulse"

FUTURE_IMPORT = "from __future__ import annotations"

UNION_PATTERN = re.compile(
    r"""
    :\s*                    # colon before type annotation
    [A-Za-z_][\w.\[\]]*    # type name (e.g., str, dict[str, Any])
    \s*\|\s*               # pipe with optional spaces
    [A-Za-z_][\w.\[\]]*    # second type
    """,
    re.VERBOSE,
)


def _python_files():
    return sorted(SRC_DIR.rglob("*.py"))


def test_all_files_with_union_syntax_have_future_annotations():
    missing = []
    for path in _python_files():
        content = path.read_text()
        if UNION_PATTERN.search(content) and FUTURE_IMPORT not in content:
            missing.append(str(path.relative_to(SRC_DIR.parent.parent)))
    assert not missing, (
        f"Files using '|' union type syntax without 'from __future__ import annotations':\n"
        + "\n".join(f"  - {f}" for f in missing)
    )


def test_src_has_python_files():
    files = _python_files()
    assert len(files) > 0, "No .py files found under src/skypulse/"
