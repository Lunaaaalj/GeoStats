#!/usr/bin/env bash
# Instala el motor LaTeX que exige docs/reporte/main.tex.
#   texlive-latex-extra : tcolorbox, enumitem, caption, float, microtype
#   texlive-lang-spanish: babel en español
#   texlive-publishers  : cas-model2-names.bst (bibliografía)
#   latexmk             : orquesta pdflatex + bibtex
#   google-chrome       : `chrome --headless --print-to-pdf` para el PDF de cada notebook
set -euo pipefail

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  texlive-latex-base texlive-latex-recommended texlive-latex-extra \
  texlive-fonts-recommended texlive-lang-spanish texlive-publishers \
  latexmk

# Chrome estable (no hay paquete .deb de Chromium en Ubuntu: es snap).
if ! command -v google-chrome >/dev/null; then
  deb="$(mktemp --suffix=.deb)"
  curl -fsSL -o "$deb" https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "$deb"
  rm -f "$deb"
fi
# CLAUDE.md invoca `chrome`; en contenedor headless exige --no-sandbox.
sudo tee /usr/local/bin/chrome >/dev/null <<'WRAP'
#!/usr/bin/env bash
exec google-chrome --no-sandbox "$@"
WRAP
sudo chmod +x /usr/local/bin/chrome

# Respaldo: si el feature falló, instala Claude Code con npm.
command -v claude >/dev/null || npm install -g @anthropic-ai/claude-code
