"""Arma el carrusel de Instagram: un PNG de 1080 × 1350 por lámina.

Reutiliza lo de la presentación (`docs/presentacion`): su `datos.json`, sus
fuentes, sus logotipos y su generador de QR. `plantilla.html` tiene una
<section class="ig"> por lámina; cada una dice en `data-archivo` cómo se llama
su PNG. Se arma el HTML con todo embebido, se abre en el Chrome instalado y se
fotografía cada lámina por separado.

    uv run --with segno --with playwright --no-project python publicacion/construir.py

Faltan a propósito el 02 (la nota periodística) y el 15 (la foto de la app):
esos los ponen los autores y la numeración ya les deja su lugar.
"""

from __future__ import annotations

import re
import sys
import tempfile
import pathlib

from playwright.sync_api import sync_playwright

AQUI = pathlib.Path(__file__).parent
PRESENTACION = AQUI.parent / "docs" / "presentacion"
sys.path.insert(0, str(PRESENTACION))

import construir as base  # noqa: E402  (el construir.py de la presentación)


def armar() -> str:
    plantilla = (AQUI / "plantilla.html").read_text(encoding="utf-8")
    salida = plantilla.replace("{{DATOS}}", base.datos())
    return re.sub(r"\{\{(FUENTE|QR_LADO|QR_TRAZO|IMG):([^}]+)\}\}", base.resolver, salida)


def main() -> None:
    html = armar()
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        pagina_html = pathlib.Path(tmp) / "carrusel.html"
        pagina_html.write_text(html, encoding="utf-8")
        navegador = p.chromium.launch(channel="chrome")
        pagina = navegador.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        pagina.goto(pagina_html.as_uri())
        pagina.wait_for_selector("body[data-listo]")
        pagina.evaluate("document.fonts.ready")
        laminas = pagina.locator("section.ig")
        for k in range(laminas.count()):
            lamina = laminas.nth(k)
            nombre = lamina.get_attribute("data-archivo")
            lamina.screenshot(path=str(AQUI / f"{nombre}.png"))
            print(f"{nombre}.png")
        navegador.close()


if __name__ == "__main__":
    main()
