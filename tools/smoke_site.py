#!/usr/bin/env python3
"""Lightweight smoke checks for MkDocs CV site files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    ROOT / "mkdocs.yml",
    ROOT / "resume.json",
    ROOT / "docs" / "index.md",
    ROOT / "docs" / "stylesheets" / "extra.css",
    ROOT / "docs" / "javascripts" / "extra.js",
    ROOT / "docs" / "assets" / "profilepic.jpg",
    ROOT / "latex" / "CV.template.tex.j2",
    ROOT / "tools" / "render_cv.py",
    ROOT / "tools" / "render_site.py",
]

REQUIRED_JSON_KEYS = [
    "basics",
    "experience",
    "certifications",
    "education",
    "skills",
    "hobbies",
    "pdf",
]

REQUIRED_BASICS_KEYS = [
    "name",
    "title",
    "email",
    "profile",
    "quote",
    "buttons",
]

REQUIRED_MARKERS = [
    "# CV",
    "## Experience",
    "## Education",
    "## Skills",
    "## Languages",
    "## Hobbies and Interests",
    "Doc-Home-ops",
]


def main() -> int:
    errors: list[str] = []

    for file_path in REQUIRED_FILES:
        if not file_path.is_file():
            errors.append(f"Missing required file: {file_path}")

    if (ROOT / "resume.json").is_file():
        resume_data = json.loads((ROOT / "resume.json").read_text(encoding="utf-8"))
        for key in REQUIRED_JSON_KEYS:
            if key not in resume_data:
                errors.append(f"resume.json missing key: {key}")

        basics = resume_data.get("basics") if isinstance(resume_data.get("basics"), dict) else {}
        for key in REQUIRED_BASICS_KEYS:
            if key not in basics:
                errors.append(f"resume.json basics missing key: {key}")

        buttons = basics.get("buttons")
        if not isinstance(buttons, list) or not buttons:
            errors.append("resume.json basics.buttons must be a non-empty array")

    if (ROOT / "docs" / "index.md").is_file():
        index_md = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
        for marker in REQUIRED_MARKERS:
            if marker not in index_md:
                errors.append(f"docs/index.md missing marker: {marker}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print("Smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
