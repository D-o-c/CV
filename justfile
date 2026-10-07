set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
export UV_CACHE_DIR := ".uv-cache"

alias b := build
alias t := test
alias s := serve

# 1Password references for the private PDF; override with CV_OP_PHONE / CV_OP_PHOTO
op_phone := env("CV_OP_PHONE", "op://Personal/CV/phone")
op_photo := env("CV_OP_PHOTO", "op://Personal/CV/profilepic.jpg")

default:
  @just --list

test:
  uv run --with mkdocs-material==9.6.14 python tools/render_site.py
  uv run python tools/smoke_site.py
  uv run python tools/render_cv.py --validate-only

build:
  rm -rf dist
  uv run --with jinja2==3.1.6 python tools/render_cv.py
  latexmk -pdf -cd latex/CV.generated.tex
  uv run --with mkdocs-material==9.6.14 python tools/render_site.py
  uv run --with mkdocs-material==9.6.14 mkdocs build --strict --site-dir dist
  cp resume.json dist/resume.json

serve addr="127.0.0.1:8000":
  uv run --with mkdocs-material==9.6.14 python tools/render_site.py
  uv run --with mkdocs-material==9.6.14 mkdocs serve --dev-addr {{addr}}

# PDF with phone and real photo from 1Password. Outputs are gitignored and never published.
build-private:
  #!/usr/bin/env bash
  set -euo pipefail
  mkdir -p latex/private
  op read --force --out-file latex/private/profilepic.jpg "{{op_photo}}" > /dev/null
  phone="$(op read --no-newline "{{op_phone}}")"
  CV_PHONE="$phone" uv run --with jinja2==3.1.6 python tools/render_cv.py --output latex/CV.private.tex --photo private/profilepic.jpg
  latexmk -pdf -cd latex/CV.private.tex
  echo "Private PDF: latex/CV.private.pdf"
