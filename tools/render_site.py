#!/usr/bin/env python3
"""Render MkDocs content from resume.json."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DOCS_INDEX = DOCS_DIR / "index.md"
DOCS_ASSETS = DOCS_DIR / "assets"
RESUME_PATH = ROOT / "resume.json"

REQUIRED_KEYS = {
    "basics",
    "experience",
    "certifications",
    "education",
    "skills",
    "hobbies",
    "pdf",
}

REQUIRED_BASICS_KEYS = {
    "name",
    "title",
    "email",
    "profile",
    "quote",
    "buttons",
}

SOFT_SKILL_LEVELS = {
    "Communication": 5,
    "Problem-Solving": 5,
    "Adaptability": 4,
    "Team Collaboration": 5,
    "Stakeholder Management": 4,
    "Critical Thinking": 5,
    "Time Management": 4,
    "Creativity": 4,
}

SOFT_SKILL_DETAILS = {
    "Adaptability": "Fast context switching across projects, tools, and organizational priorities.",
    "Communication": "Clear communication across technical and non-technical stakeholders.",
    "Critical Thinking": "Structured analysis of risks, assumptions, and tradeoffs before execution.",
    "Problem-Solving": "Pragmatic problem decomposition and delivery-focused resolution under constraints.",
    "Stakeholder Management": "Cross-functional alignment with engineering, operations, risk, and governance teams.",
    "Team Collaboration": "Consistent collaboration in distributed teams with shared ownership and feedback loops.",
    "Time Management": "Prioritization and focus management to deliver reliably across parallel initiatives.",
    "Creativity": "Solution design that balances standards, constraints, and practical innovation.",
}


def proficiency_to_level(proficiency: str) -> int:
    value = proficiency.lower()
    if "native" in value or "c2" in value:
        return 5
    if "c1" in value or "advanced" in value or "professional" in value:
        return 4
    if "b2" in value or "upper" in value or "good" in value:
        return 3
    if "b1" in value or "intermediate" in value:
        return 2
    return 1


def clamp_level(value: Any, default: int = 4) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(5, level))


def fail(message: str) -> None:
    raise ValueError(message)


def read_resume() -> dict[str, Any]:
    if not RESUME_PATH.is_file():
        fail(f"Missing resume.json at {RESUME_PATH}")

    try:
        data = json.loads(RESUME_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid resume.json: {exc}")

    missing_top = sorted(REQUIRED_KEYS - data.keys())
    if missing_top:
        fail(f"resume.json missing top-level keys: {', '.join(missing_top)}")

    basics = data.get("basics")
    if not isinstance(basics, dict):
        fail("resume.json basics must be an object")

    missing_basics = sorted(REQUIRED_BASICS_KEYS - basics.keys())
    if missing_basics:
        fail(f"resume.json basics missing keys: {', '.join(missing_basics)}")

    buttons = basics.get("buttons")
    if not isinstance(buttons, list) or not buttons:
        fail("resume.json basics.buttons must be a non-empty array")

    for idx, button in enumerate(buttons):
        if not isinstance(button, dict):
            fail(f"resume.json basics.buttons[{idx}] must be an object")
        label = str(button.get("label", "")).strip()
        icon = str(button.get("icon", "")).strip()
        href = str(button.get("href", "")).strip()
        requires_asset = (
            str(button.get("requires_asset", "")).strip()
            or str(button.get("requiresAsset", "")).strip()
        )
        if not label:
            fail(f"resume.json basics.buttons[{idx}] missing non-empty 'label'")
        if not icon:
            fail(f"resume.json basics.buttons[{idx}] missing non-empty 'icon'")
        if not href and not requires_asset:
            fail(
                f"resume.json basics.buttons[{idx}] must define 'href' "
                "or 'requires_asset'"
            )

    return data


def ensure_profile_photo(resume: dict[str, Any]) -> dict[str, str]:
    pdf = resume.get("pdf", {}) if isinstance(resume.get("pdf"), dict) else {}
    source_name = str(pdf.get("photo_filename", "profilepic.jpg")).strip() or "profilepic.jpg"

    source_path = ROOT / "latex" / source_name
    if not source_path.is_file():
        fail(
            "Missing profile image for website/PDF. Expected file: "
            f"{source_path}"
        )

    DOCS_ASSETS.mkdir(parents=True, exist_ok=True)

    source_suffix = source_path.suffix.lower() or ".jpg"
    source_stem = source_path.stem

    main_target_name = f"profilepic{source_suffix}"
    main_target_path = DOCS_ASSETS / main_target_name
    shutil.copyfile(source_path, main_target_path)

    variants = {
        "hero": source_path.parent / f"{source_stem}-hero{source_suffix}",
        "mobile": source_path.parent / f"{source_stem}-mobile{source_suffix}",
        "preview": source_path.parent / f"{source_stem}-preview{source_suffix}",
    }

    profile_images = {
        "main": f"assets/{main_target_name}",
        "hero": f"assets/{main_target_name}",
        "mobile": f"assets/{main_target_name}",
        "preview": f"assets/{main_target_name}",
    }

    for key, variant_source_path in variants.items():
        if not variant_source_path.is_file():
            continue
        variant_target_name = f"profilepic-{key}{source_suffix}"
        variant_target_path = DOCS_ASSETS / variant_target_name
        shutil.copyfile(variant_source_path, variant_target_path)
        profile_images[key] = f"assets/{variant_target_name}"

    return profile_images


def sync_pdf_asset() -> bool:
    source_path = ROOT / "latex" / "CV.generated.pdf"
    target_path = DOCS_ASSETS / "MattiaPini_CV.pdf"

    if source_path.is_file():
        DOCS_ASSETS.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
        return True

    return target_path.is_file()


def parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


@lru_cache(maxsize=1)
def mkdocs_icon_root() -> Path | None:
    try:
        import material  # type: ignore
    except Exception:  # noqa: BLE001
        return None

    root = Path(material.__file__).resolve().parent / "templates" / ".icons"
    if root.is_dir():
        return root
    return None


def mkdocs_icon_parts(icon_raw: str, icon_type: str) -> tuple[str, ...] | None:
    token = icon_raw.strip()
    if token.startswith(":") and token.endswith(":") and len(token) > 2:
        token = token[1:-1]

    token = token.strip().lower().replace("_", "-")
    token = re.sub(r"[^a-z0-9/\-]", "", token)
    if not token:
        return None

    if "/" in token:
        parts = tuple(part for part in token.split("/") if part)
        return parts if parts else None

    if token.startswith("fontawesome-"):
        remaining = token[len("fontawesome-") :]
        style, sep, name = remaining.partition("-")
        if sep and style and name:
            return ("fontawesome", style, name)
        return None

    known_prefixes = {"material", "simple", "octicons", "logos"}
    if "-" in token:
        prefix, remainder = token.split("-", 1)
        if prefix in known_prefixes and remainder:
            return (prefix, remainder)

    if icon_type in {"material", "mkdocs-material", "md"}:
        return ("material", token)

    return ("material", token)


def render_mkdocs_svg(icon_raw: str, icon_type: str) -> str | None:
    root = mkdocs_icon_root()
    if root is None:
        return None

    parts = mkdocs_icon_parts(icon_raw, icon_type)
    if not parts:
        return None

    if any(not re.fullmatch(r"[a-z0-9\-]+", part) for part in parts):
        return None

    icon_path = (root / Path(*parts)).with_suffix(".svg")
    try:
        resolved_root = root.resolve()
        resolved_icon = icon_path.resolve()
    except OSError:
        return None

    if resolved_root not in resolved_icon.parents or not resolved_icon.is_file():
        return None

    svg = resolved_icon.read_text(encoding="utf-8").strip()
    if "<svg" not in svg:
        return None

    svg = re.sub(
        r"<svg\b",
        '<svg aria-hidden="true" focusable="false"',
        svg,
        count=1,
    )
    return svg


def render_button_icon(button: dict[str, Any], icon_raw: str) -> str:
    icon_type = (
        str(button.get("icon_type", "")).strip().lower()
        or str(button.get("iconType", "")).strip().lower()
    )
    icon_aria = html.escape(str(button.get("icon_aria_label", "")).strip())

    if icon_type in {"fa", "fontawesome"}:
        safe_classes = re.sub(r"[^a-zA-Z0-9\-\s]", "", icon_raw).strip()
        if safe_classes:
            aria_attr = f' aria-label="{icon_aria}"' if icon_aria else ""
            return (
                "<span class=\"cv-chip__icon cv-chip__icon--fa\""
                f"{aria_attr}>"
                f"<i class=\"{html.escape(safe_classes)}\" aria-hidden=\"true\"></i>"
                "</span>"
            )

    if icon_type in {"material", "mkdocs-material", "md", "mkdocs", "emoji"}:
        svg_markup = render_mkdocs_svg(icon_raw, icon_type)
        if svg_markup:
            aria_attr = f' aria-label="{icon_aria}"' if icon_aria else ""
            return (
                "<span class=\"cv-chip__icon cv-chip__icon--mkdocs\""
                f"{aria_attr}>"
                f"{svg_markup}"
                "</span>"
            )

    aria_attr = f' aria-label="{icon_aria}"' if icon_aria else ""
    return (
        "<span class=\"cv-chip__icon\""
        f"{aria_attr}>"
        f"{html.escape(icon_raw)}"
        "</span>"
    )


def asset_exists(asset_ref: str, has_pdf_asset: bool) -> bool:
    normalized = asset_ref.strip().lstrip("/")
    if normalized in {"assets/MattiaPini_CV.pdf", "docs/assets/MattiaPini_CV.pdf"}:
        return has_pdf_asset

    if normalized.startswith("docs/"):
        target_path = ROOT / normalized
    elif normalized.startswith("assets/"):
        target_path = DOCS_DIR / normalized
    else:
        target_path = ROOT / normalized
    return target_path.is_file()


def infer_experience_logo(company: str) -> str | None:
    normalized = company.casefold()
    if "unicredit" in normalized:
        return "assets/logos/unicredit-services.svg"
    if "horizon consulting" in normalized:
        return "assets/logos/horizon-consulting.svg"
    if "grancasa" in normalized or "expert" in normalized:
        return "assets/logos/grancasa-expert.svg"
    if "nous" in normalized:
        return "assets/logos/nous-srl.svg"
    return None


def company_initials(company: str) -> str:
    words = [part for part in re.split(r"[^A-Za-z0-9]+", company) if part]
    if not words:
        return "CV"
    return "".join(part[0].upper() for part in words[:2])


def write_markdown(resume: dict[str, Any], profile_images: dict[str, str], has_pdf_asset: bool) -> None:
    basics = resume["basics"]

    lines: list[str] = []
    lines.append("# CV")
    lines.append("")
    lines.append('<div class="cv-hero reveal">')
    lines.append(
        '  <div class="cv-hero__photo" role="button" tabindex="0" aria-label="Toggle profile image zoom">'
    )
    lines.append('    <picture class="cv-hero__picture">')
    if profile_images["mobile"] != profile_images["hero"]:
        lines.append(
            "      "
            f"<source media=\"(max-width: 840px)\" srcset=\"{profile_images['mobile']}\" />"
        )
    lines.append(
        "      "
        f"<img class=\"cv-hero__photo-main\" src=\"{profile_images['hero']}\" alt=\"{html.escape(basics['name'])} profile picture\" loading=\"eager\" />"
    )
    lines.append("    </picture>")
    lines.append('    <div class="cv-hero__photo-preview" aria-hidden="true">')
    lines.append(
        "      "
        f"<img src=\"{profile_images['preview']}\" alt=\"\" loading=\"lazy\" />"
    )
    lines.append("    </div>")
    lines.append("  </div>")
    lines.append('  <div class="cv-hero__content">')
    lines.append(f"    <h2 class=\"cv-hero__name\">{html.escape(basics['name'])}</h2>")
    lines.append(f"    <p class=\"cv-hero__role\">{html.escape(basics['title'])}</p>")
    lines.append(f"    <p>{html.escape(basics['profile'])}</p>")
    lines.append(f"    <p class=\"cv-hero__quote\">\"{html.escape(basics['quote'])}\"</p>")
    lines.append('    <div class="cv-link-grid">')
    buttons = basics.get("buttons", [])
    for button in buttons:
        if not isinstance(button, dict):
            continue

        label_raw = str(button.get("label", "")).strip()
        icon_raw = str(button.get("icon", "")).strip()
        href_raw = str(button.get("href", "")).strip()
        if not label_raw or not icon_raw:
            continue

        variant_raw = str(button.get("variant", "")).strip().lower()
        variant = re.sub(r"[^a-z0-9-]+", "", variant_raw)
        classes = ["cv-chip", "cv-chip--icononly"]
        if variant:
            classes.append(f"cv-chip--{variant}")
        if parse_bool(button.get("accent"), default=False):
            classes.append("cv-chip--accent")
        class_attr = " ".join(classes)

        label = html.escape(label_raw)
        icon_markup = render_button_icon(button, icon_raw)
        title = html.escape(str(button.get("title", label_raw)).strip() or label_raw)
        aria_label = html.escape(str(button.get("aria_label", label_raw)).strip() or label_raw)
        disabled_label_raw = (
            str(button.get("disabled_label", "")).strip()
            or str(button.get("disabledLabel", "")).strip()
            or label_raw
        )
        disabled_label = html.escape(disabled_label_raw)
        requires_asset_raw = (
            str(button.get("requires_asset", "")).strip()
            or str(button.get("requiresAsset", "")).strip()
        )

        if requires_asset_raw and not asset_exists(requires_asset_raw, has_pdf_asset):
            lines.append(
                "      "
                f"<span class=\"cv-chip cv-chip--disabled\">{icon_markup}<span>{disabled_label}</span></span>"
            )
            continue

        if not href_raw:
            continue

        href = html.escape(href_raw)
        external_default = href_raw.startswith("http://") or href_raw.startswith("https://")
        external = parse_bool(button.get("external"), default=external_default)
        target_attrs = ' target="_blank" rel="noopener"' if external else ""

        lines.append(
            "      "
            f"<a class=\"{class_attr}\" href=\"{href}\"{target_attrs} title=\"{title}\" aria-label=\"{aria_label}\">{icon_markup}<span class=\"cv-chip__label\">{label}</span></a>"
        )
    lines.append("    </div>")
    lines.append("  </div>")
    lines.append("</div>")
    lines.append("")

    lines.append("## Experience")
    lines.append("")
    lines.append('<div class="cv-timeline">')
    for item in resume["experience"]:
        role = html.escape(item.get("role", ""))
        company_raw = str(item.get("company", ""))
        company = html.escape(company_raw)
        subtitle = html.escape(item.get("subtitle", ""))
        location = html.escape(item.get("location", ""))
        period = html.escape(item.get("period", ""))
        logo_custom = str(item.get("logo", "")).strip()
        logo_path = logo_custom if logo_custom else infer_experience_logo(company_raw)
        initials = html.escape(company_initials(company_raw))

        lines.append('  <article class="cv-card reveal">')
        lines.append('    <header class="cv-card__header cv-card__header--with-logo">')
        lines.append('      <div class="cv-card__title-wrap">')
        if logo_path:
            lines.append(
                "        "
                f"<span class=\"cv-company-logo\"><img src=\"{html.escape(logo_path)}\" alt=\"{company} logo\" loading=\"lazy\" /></span>"
            )
        else:
            lines.append(
                "        "
                f"<span class=\"cv-company-logo cv-company-logo--fallback\" aria-hidden=\"true\">{initials}</span>"
            )
        lines.append(f"        <h3>{role}</h3>")
        lines.append("      </div>")
        lines.append(f"      <p class=\"cv-card__period\">{period}</p>")
        lines.append("    </header>")

        meta_parts = [part for part in (company, location, subtitle) if part]
        if meta_parts:
            lines.append(f"    <p class=\"cv-card__meta\">{' · '.join(meta_parts)}</p>")

        details = item.get("details", [])
        if details:
            lines.append("    <ul>")
            for detail in details:
                lines.append(f"      <li>{html.escape(str(detail))}</li>")
            lines.append("    </ul>")

        lines.append("  </article>")
    lines.append("</div>")
    lines.append("")

    talks = resume.get("talks", [])
    if talks:
        lines.append("## Talks and Workshops")
        lines.append("")
        lines.append('<div class="cv-timeline">')
        for talk in talks:
            title = html.escape(str(talk.get("title", "")))
            url = str(talk.get("url", "")).strip()
            if url:
                title = f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{title}</a>'
            meta_parts = [
                html.escape(str(talk.get(key, "")).strip())
                for key in ("type", "event", "location")
                if str(talk.get(key, "")).strip()
            ]
            lines.append('  <article class="cv-card reveal">')
            lines.append('    <header class="cv-card__header">')
            lines.append(f"      <h3>{title}</h3>")
            lines.append(f"      <p class=\"cv-card__period\">{html.escape(str(talk.get('year', '')))}</p>")
            lines.append("    </header>")
            if meta_parts:
                lines.append(f"    <p class=\"cv-card__meta\">{' · '.join(meta_parts)}</p>")
            details = str(talk.get("details", "")).strip()
            if details:
                lines.append(f"    <p>{html.escape(details)}</p>")
            lines.append("  </article>")
        lines.append("</div>")
        lines.append("")

    awards = resume.get("awards", [])
    if awards:
        lines.append("## Awards")
        lines.append("")
        for award in awards:
            year = html.escape(str(award.get("year", "")))
            name = html.escape(str(award.get("name", "")))
            event = html.escape(str(award.get("event", "")))
            details = str(award.get("details", "")).strip()
            suffix = f" — {html.escape(details)}" if details else ""
            lines.append(f"- **{year}** — {name}, {event}{suffix}")
        lines.append("")

    lines.append("## Certifications")
    lines.append("")
    if resume["certifications"]:
        for cert in resume["certifications"]:
            year = html.escape(str(cert.get("year", "")))
            name = html.escape(cert.get("name", ""))
            issuer = html.escape(cert.get("issuer", ""))
            lines.append(f"- **{year}** — {name} ({issuer})")
    else:
        lines.append("- No certifications listed.")
    lines.append("")

    lines.append("## Education")
    lines.append("")
    lines.append('<div class="cv-grid cv-grid--education">')
    for item in resume["education"]:
        period = html.escape(item.get("period", ""))
        degree = html.escape(item.get("degree", ""))
        institution = html.escape(item.get("institution", ""))
        field = html.escape(str(item.get("field", "")).strip())

        lines.append('  <article class="cv-card reveal">')
        lines.append(f"    <h3>{degree}</h3>")
        lines.append(f"    <p class=\"cv-card__period\">{period}</p>")
        lines.append(f"    <p class=\"cv-card__meta\">{institution}</p>")
        if field:
            lines.append(f"    <p class=\"cv-card__field\">{field}</p>")
        lines.append("  </article>")
    lines.append("</div>")
    lines.append("")

    lines.append("## Skills")
    lines.append("")
    lines.append('<div class="cv-grid cv-grid--skills">')
    lines.append('  <article class="cv-card reveal">')
    lines.append("    <h3>Technical</h3>")
    lines.append('    <div class="cv-meter-list">')
    technical_skills = sorted(
        resume["skills"]["technical"],
        key=lambda item: str(item.get("category", "")).casefold(),
    )
    for skill in technical_skills:
        category = html.escape(skill.get("category", ""))
        details = html.escape(skill.get("details", ""))
        level = clamp_level(skill.get("level", 4))
        percent = level * 20
        track_class = "cv-meter-track cv-meter-track--full" if level == 5 else "cv-meter-track"
        lines.append(
            '      <article class="cv-meter-item cv-meter-item--has-details" role="button" tabindex="0">'
        )
        lines.append('        <div class="cv-meter-face cv-meter-face--front">')
        lines.append('          <div class="cv-meter-head">')
        lines.append(f"            <span>{category}</span>")
        lines.append(f'            <span class="cv-meter-score">{level}/5</span>')
        lines.append("          </div>")
        lines.append(
            f'          <div class="{track_class}" role="img" aria-label="{category} proficiency {level} out of 5"><span style="width:{percent}%"></span></div>'
        )
        lines.append("        </div>")
        lines.append('        <div class="cv-meter-face cv-meter-face--back" aria-hidden="true">')
        lines.append(f'          <p class="cv-meter-detail-title">{category}</p>')
        lines.append(f'          <p class="cv-meter-detail-text">{details}</p>')
        lines.append('          <p class="cv-meter-detail-hint">Tap or press Enter to return</p>')
        lines.append("        </div>")
        lines.append("      </article>")
    lines.append("    </div>")
    lines.append("  </article>")

    lines.append('  <article class="cv-card reveal">')
    lines.append("    <h3>Soft Skills</h3>")
    lines.append('    <div class="cv-meter-list">')
    soft_skills = sorted((str(skill) for skill in resume["skills"]["soft"]), key=str.casefold)
    for skill in soft_skills:
        label = html.escape(str(skill))
        level = clamp_level(SOFT_SKILL_LEVELS.get(str(skill), 4))
        details = html.escape(
            SOFT_SKILL_DETAILS.get(str(skill), f"{str(skill)} applied to delivery across enterprise programs.")
        )
        percent = level * 20
        track_class = "cv-meter-track cv-meter-track--full" if level == 5 else "cv-meter-track"
        lines.append(
            '      <article class="cv-meter-item cv-meter-item--has-details" role="button" tabindex="0">'
        )
        lines.append('        <div class="cv-meter-face cv-meter-face--front">')
        lines.append('          <div class="cv-meter-head">')
        lines.append(f"            <span>{label}</span>")
        lines.append(f'            <span class="cv-meter-score">{level}/5</span>')
        lines.append("          </div>")
        lines.append(
            f'          <div class="{track_class}" role="img" aria-label="{label} proficiency {level} out of 5"><span style="width:{percent}%"></span></div>'
        )
        lines.append("        </div>")
        lines.append('        <div class="cv-meter-face cv-meter-face--back" aria-hidden="true">')
        lines.append(f'          <p class="cv-meter-detail-title">{label}</p>')
        lines.append(f'          <p class="cv-meter-detail-text">{details}</p>')
        lines.append('          <p class="cv-meter-detail-hint">Tap or press Enter to return</p>')
        lines.append("        </div>")
        lines.append("      </article>")
    lines.append("    </div>")
    lines.append("  </article>")
    lines.append("</div>")
    lines.append("")

    lines.append("## Languages")
    lines.append("")
    lines.append('<div class="cv-language-grid">')
    for language in resume["skills"]["languages"]:
        name = html.escape(language.get("language", ""))
        proficiency = html.escape(language.get("proficiency", ""))
        level = proficiency_to_level(proficiency)

        lines.append('  <article class="cv-card reveal cv-language-item">')
        lines.append('    <div class="cv-language-head">')
        lines.append('      <div class="cv-language-meta">')
        lines.append(f"        <strong>{name}</strong>")
        lines.append(f"        <span>{proficiency}</span>")
        lines.append("      </div>")
        lines.append(
            f'      <div class="cv-dots" role="img" aria-label="{level} out of 5 proficiency">'
        )
        for idx in range(5):
            cls = "cv-dot is-filled" if idx < level else "cv-dot"
            lines.append(f'        <span class="{cls}" aria-hidden="true"></span>')
        lines.append("      </div>")
        lines.append("    </div>")
        lines.append("  </article>")
    lines.append("</div>")
    lines.append("")

    lines.append("## Hobbies and Interests")
    lines.append("")
    lines.append('<div class="cv-card reveal">')
    lines.append("  <ul>")
    for hobby in resume["hobbies"]:
        lines.append(f"    <li>{html.escape(str(hobby))}</li>")
    lines.append("  </ul>")
    lines.append("</div>")
    lines.append("")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_INDEX.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    try:
        resume = read_resume()
        profile_images = ensure_profile_photo(resume)
        has_pdf_asset = sync_pdf_asset()
        write_markdown(resume, profile_images, has_pdf_asset)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Generated {DOCS_INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
