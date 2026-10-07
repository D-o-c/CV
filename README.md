# CV Website + PDF Pipeline

This repository builds:

- A polished MkDocs website (`docs/`) generated from `resume.json`
- A PDF CV (`moderncv`) generated from the same `resume.json`

`resume.json` is the single source of truth.

## Stack

- Website: MkDocs + Material theme + custom CSS/JS
- PDF: LaTeX (`moderncv`) rendered via Jinja2
- Tooling: `uv` + `just`

## Structure

- `resume.json`: canonical CV data source
- `mkdocs.yml`: MkDocs configuration
- `docs/index.md`: generated page content from JSON
- `docs/stylesheets/extra.css`: custom visual design
- `docs/javascripts/extra.js`: reveal transitions
- `tools/render_site.py`: JSON -> `docs/index.md` (+ profile photo sync)
- `latex/CV.template.tex.j2`: Jinja2 LaTeX template
- `tools/render_cv.py`: JSON validation + JSON -> LaTeX
- `.github/workflows/pages.yml`: CI build + Pages deploy

## Prerequisites

- `uv`
- `just`
- LaTeX with `latexmk` and `moderncv`

## Required assets

- Required: `latex/profilepic.jpg` (or the filename set in `resume.json -> pdf.photo_filename`)

Optional website variants (same extension and base name as `photo_filename`, placed in `latex/`):

- `<base>-hero.<ext>`: desktop hero crop
- `<base>-mobile.<ext>`: mobile hero crop
- `<base>-preview.<ext>`: enlarged click/tap preview

Example if `photo_filename` is `profilepic.jpg`:

- `latex/profilepic-hero.jpg`
- `latex/profilepic-mobile.jpg`
- `latex/profilepic-preview.jpg`

If variants are missing, the base image is reused for all contexts.

## Local commands

Run checks:

```bash
just test
```

Build full artifact (`dist/`):

```bash
just build
```

`just build` also ensures PDF is available at `assets/MattiaPini_CV.pdf` inside the generated site.

Serve locally with live reload:

```bash
just serve
```

`just serve` starts the local site without forcing LaTeX compilation.  
If `latex/CV.generated.pdf` exists, the Download PDF button is active; otherwise the page shows a disabled hint.

Then open `http://127.0.0.1:8000`.

Build the private PDF (phone number and real photo from 1Password):

```bash
just build-private
```

It reads `op://Personal/CV/phone` and the `profilepic.jpg` file attached to the same item
(override with `CV_OP_PHONE` / `CV_OP_PHOTO`) and writes `latex/CV.private.pdf`.
The photo, the generated files and the PDF are gitignored and never reach the website.

## CI / Deployment

Workflow triggers:

- `push` on `main`
- `pull_request` (build and validation only)
- `workflow_dispatch`

Pipeline flow:

1. Validate resume schema and required assets
2. Generate MkDocs markdown from JSON
3. Generate LaTeX from JSON and compile PDF
4. Build MkDocs site to `dist/`
5. Copy `MattiaPini_CV.pdf` and `resume.json` into `dist/`
6. Deploy `dist/` to GitHub Pages

## Updating CV content

Edit only `resume.json`, then run `just build`.

## Customizing Header Buttons

Header buttons are fully data-driven from `resume.json -> basics.buttons`.
You can add, remove, reorder, or change icons/links without editing code.

Button fields:

- `label` (required): button text shown on hover/focus
- `icon` (required): emoji/text icon shown in compact state
- `icon_type` (optional): `text` (default), `fa`/`fontawesome`, or `mkdocs`/`material`/`md`
- `href` (required unless you only show disabled state): link target
- `variant` (optional): adds CSS class `cv-chip--<variant>` for styling
- `external` (optional): open in new tab (`true`/`false`)
- `accent` (optional): adds accent visual style
- `requires_asset` (optional): if file is missing, button is rendered disabled
- `disabled_label` (optional): text to show in disabled state
- `title` / `aria_label` (optional): accessibility and tooltip labels

Example:

```json
{
  "label": "Portfolio",
  "icon": "★",
  "href": "https://example.com",
  "variant": "portfolio",
  "external": true
}
```

Font Awesome icon example:

```json
{
  "label": "LinkedIn",
  "icon": "fa-brands fa-linkedin-in",
  "icon_type": "fa",
  "href": "https://www.linkedin.com/in/MattiaPini",
  "variant": "linkedin",
  "external": true
}
```

MkDocs Material icon/emoji example:

```json
{
  "label": "Email",
  "icon": ":material-email:",
  "icon_type": "mkdocs",
  "href": "mailto:you@example.com",
  "variant": "email"
}
```

You can use any shortcode from the Material icon reference, e.g.:
- `:material-linkedin:`
- `:fontawesome-brands-github:`
- `:simple-kubernetes:`

For `icon_type: "mkdocs"`, these shorthand forms are also accepted:
- `material-email`
- `material/email`
- `simple-kubernetes`
