"""Collapse multiline Django/Jinja tags into single lines.

Django/Jinja tags like {{ ... }} and {% ... %} MUST NOT be split across
multiple lines. This script joins any such tag that spans lines into a
single line so that djlint can format the template without breaking
template syntax.
"""
import re
import sys
from pathlib import Path

TAG_PATTERN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)


def collapse(text: str) -> str:
    def join(match: re.Match) -> str:
        return re.sub(r"\s*\n\s*", " ", match.group(0))

    return TAG_PATTERN.sub(join, text)


def main(paths: list[str]) -> int:
    changed = 0
    for p in paths:
        fp = Path(p)
        if not fp.is_file():
            continue
        original = fp.read_text(encoding="utf-8")
        updated = collapse(original)
        if updated != original:
            fp.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"collapsed {changed} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
