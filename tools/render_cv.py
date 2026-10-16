#!/usr/bin/env python3
"""Render a moderncv LaTeX file from resume.json using Jinja2."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL_KEYS = {
    "basics",
    "experience",
    "certifications",
    "education",
    "skills",
    "hobbies",
}

REQUIRED_BASICS_KEYS = {
    "name",
    "title",
    "email",
    "linkedin",
    "profile",
    "quote",
}

REQUIRED_SKILLS_KEYS = {"technical", "languages", "soft"}


def latex_escape(value: Any) -> str:
    """Escape text for safe insertion into LaTeX."""
    if value is None:
        return ""

    text = str(value)
    replacements = (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    )

    for src, target in replacements:
        text = text.replace(src, target)

    return text


def pairwise(items: list[str]) -> list[tuple[str, str]]:
    """Create pairs for moderncv's cvlistdoubleitem command."""
    result: list[tuple[str, str]] = []
    for idx in range(0, len(items), 2):
        left = items[idx]
        right = items[idx + 1] if idx + 1 < len(items) else ""
        result.append((left, right))
    return result


def split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def validate_resume(data: dict[str, Any]) -> None:
    errors: list[str] = []

    missing_top_level = sorted(REQUIRED_TOP_LEVEL_KEYS - data.keys())
    if missing_top_level:
        errors.append(f"missing top-level keys: {', '.join(missing_top_level)}")

    basics = data.get("basics")
    if not isinstance(basics, dict):
        errors.append("'basics' must be an object")
    else:
        missing_basics = sorted(REQUIRED_BASICS_KEYS - basics.keys())
        if missing_basics:
            errors.append(f"missing basics keys: {', '.join(missing_basics)}")

    experience = data.get("experience")
    if not isinstance(experience, list):
        errors.append("'experience' must be an array")

    certifications = data.get("certifications")
    if not isinstance(certifications, list):
        errors.append("'certifications' must be an array")

    education = data.get("education")
    if not isinstance(education, list):
        errors.append("'education' must be an array")

    hobbies = data.get("hobbies")
    if not isinstance(hobbies, list):
        errors.append("'hobbies' must be an array")

    skills = data.get("skills")
    if not isinstance(skills, dict):
        errors.append("'skills' must be an object")
    else:
        missing_skills = sorted(REQUIRED_SKILLS_KEYS - skills.keys())
        if missing_skills:
            errors.append(f"missing skills keys: {', '.join(missing_skills)}")
        else:
            if not isinstance(skills.get("technical"), list):
                errors.append("'skills.technical' must be an array")
            if not isinstance(skills.get("languages"), list):
                errors.append("'skills.languages' must be an array")
            if not isinstance(skills.get("soft"), list):
                errors.append("'skills.soft' must be an array")

    for idx, item in enumerate(experience or []):
        if not isinstance(item, dict):
            errors.append(f"experience[{idx}] must be an object")
            continue
        for key in ("period", "role", "company"):
            if key not in item:
                errors.append(f"experience[{idx}] missing '{key}'")
        if "details" in item and not isinstance(item["details"], list):
            errors.append(f"experience[{idx}].details must be an array")
    optional_sections = {
        "talks": ("year", "title", "event"),
        "awards": ("year", "name", "event"),
    }
    for section, required in optional_sections.items():
        items = data.get(section, [])
        if not isinstance(items, list):
            errors.append(f"'{section}' must be an array")
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{section}[{idx}] must be an object")
                continue
            for key in required:
                if key not in item:
                    errors.append(f"{section}[{idx}] missing '{key}'")

    for idx, item in enumerate(education or []):
        if not isinstance(item, dict):
            errors.append(f"education[{idx}] must be an object")
            continue
        for key in ("period", "degree", "institution"):
            if key not in item:
                errors.append(f"education[{idx}] missing '{key}'")

    if errors:
        formatted = "\n - ".join(errors)
        raise ValueError(f"Resume validation failed:\n - {formatted}")


def build_context(
    data: dict[str, Any],
    phone: str = "",
    photo: str = "",
) -> dict[str, Any]:
    basics = dict(data["basics"])
    first_name, last_name = split_name(basics.get("name", ""))

    basics["first_name"] = first_name
    basics["last_name"] = last_name
    basics["phone"] = phone

    pdf_defaults = {
        "photo_filename": "profilepic.jpg",
        "gdpr_notice": (
            "In compliance with the GDPR and Italian Legislative Decree no. 196 dated "
            "30/06/2003, I hereby authorize the recipient of this document to use and "
            "process my personal details for the purpose of recruiting and selecting "
            "staff and I confirm to be informed of my rights in accordance to art. 7 "
            "of the above mentioned Decree."
        ),
        "photo_height": "64pt",
        "photo_frame": "0.4pt",
        "geometry_scale": "0.75",
    }
    pdf = dict(pdf_defaults)
    if isinstance(data.get("pdf"), dict):
        pdf.update(data["pdf"])
    if photo:
        pdf["photo_filename"] = photo

    soft_skills = data["skills"].get("soft", [])

    return {
        "basics": basics,
        "experience": data["experience"],
        "talks": data.get("talks", []),
        "awards": data.get("awards", []),
        "certifications": data["certifications"],
        "education": data["education"],
        "skills": data["skills"],
        "hobbies": data["hobbies"],
        "pdf": pdf,
        "soft_skill_pairs": pairwise(soft_skills),
    }


def check_required_assets(output_path: Path, pdf_cfg: dict[str, Any]) -> None:
    output_dir = output_path.parent

    for field in ("photo_filename",):
        file_name = str(pdf_cfg.get(field, "")).strip()
        if not file_name:
            raise ValueError(f"Missing required PDF setting: pdf.{field}")

        asset_path = output_dir / file_name
        if not asset_path.is_file():
            raise FileNotFoundError(
                "Missing required asset file: "
                f"{asset_path}\n"
                "Add the file or update resume.json -> pdf settings."
            )


def render_template(template_path: Path, output_path: Path, context: dict[str, Any]) -> None:
    try:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency 'jinja2'. Run with uv, for example: "
            "'uv run --with jinja2==3.1.6 python tools/render_cv.py'."
        ) from exc

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["latex_escape"] = latex_escape

    template = env.get_template(template_path.name)
    rendered = template.render(**context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render CV LaTeX from resume JSON.")
    parser.add_argument(
        "--input",
        default="resume.json",
        help="Path to the source resume JSON file (default: resume.json)",
    )
    parser.add_argument(
        "--template",
        default="latex/CV.template.tex.j2",
        help="Path to the Jinja2 LaTeX template",
    )
    parser.add_argument(
        "--output",
        default="latex/CV.generated.tex",
        help="Path for generated LaTeX output",
    )
    parser.add_argument(
        "--photo",
        default="",
        help="Override pdf.photo_filename, relative to the output directory (private builds)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate JSON structure and required assets without rendering output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    template_path = Path(args.template)
    output_path = Path(args.output)

    if not input_path.is_file():
        print(f"Input JSON not found: {input_path}", file=sys.stderr)
        return 1

    if not template_path.is_file():
        print(f"Template not found: {template_path}", file=sys.stderr)
        return 1

    try:
        data = read_json(input_path)
        validate_resume(data)
        # The phone comes from the environment so it never lands in argv or resume.json.
        context = build_context(data, phone=os.environ.get("CV_PHONE", ""), photo=args.photo)
        check_required_assets(output_path, context["pdf"])

        if args.validate_only:
            print("Validation passed: resume schema and PDF assets are valid.")
            return 0

        render_template(template_path, output_path, context)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Generated {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
