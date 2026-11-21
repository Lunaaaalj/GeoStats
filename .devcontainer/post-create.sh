#!/usr/bin/env bash
# Instala el motor LaTeX que exige docs/reporte/main.tex.
#   texlive-latex-extra : tcolorbox, enumitem, caption, float, microtype
#   texlive-lang-spanish: babel en español
#   texlive-publishers  : cas-model2-names.bst (bibliografía)
#   latexmk             : orquesta pdflatex + bibtex
set -euo pipefail

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  texlive-latex-base texlive-latex-recommended texlive-latex-extra \
  texlive-fonts-recommended texlive-lang-spanish texlive-publishers \
  latexmk

# Respaldo: si el feature falló, instala Claude Code con npm.
command -v claude >/dev/null || npm install -g @anthropic-ai/claude-code
