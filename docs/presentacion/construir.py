"""Arma docs/presentacion/index.html: un solo archivo, sin dependencias de red.

Toma `plantilla.html` y sustituye cada marca por el recurso ya codificado:

    {{FUENTE:...}}     archivo .woff2 de fuentes/, en base64
    {{QR_LADO:<url>}}  módulos por lado del QR de esa liga (para el viewBox)
    {{QR_TRAZO:<url>}} el trazado SVG de ese mismo QR
    {{IMG:<archivo>}}  un PNG de logos/, en base64 (solo los logotipos de la portada)
    {{DATOS}}          `datos.json` completo (lo genera `datos.py`)

No hay ni una imagen: los mapas, la curva de concentración y el calendario se
dibujan en el navegador desde `datos.json`. Por eso el archivo pesa un tercio
de MB y las gráficas comparten tipografía y paleta con el resto.

    uv run --with segno python docs/presentacion/construir.py
"""

from __future__ import annotations

import base64
import pathlib
import re

import segno

AQUI = pathlib.Path(__file__).parent
FUENTES = AQUI / "fuentes"


def fuente(nombre: str) -> str:
    """Devuelve un .woff2 como data URI."""
    b64 = base64.b64encode((FUENTES / f"{nombre}.woff2").read_bytes()).decode("ascii")
    return f"data:font/woff2;base64,{b64}"


def imagen(nombre: str) -> str:
    """Devuelve un PNG de logos/ como data URI."""
    b64 = base64.b64encode((AQUI / "logos" / nombre).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def qr(url: str) -> tuple[int, str]:
    """QR como un `path` con un tramo horizontal por corrida de módulos oscuros.

    Devuelve (módulos por lado, atributo `d`). Un rectángulo por corrida pesa
    una décima parte que uno por módulo y dibuja exactamente lo mismo.
    """
    matriz = segno.make(url, error="m").matrix
    tramos = []
    for y, fila in enumerate(matriz):
        x = 0
        while x < len(fila):
            if fila[x]:
                inicio = x
                while x < len(fila) and fila[x]:
                    x += 1
                tramos.append(f"M{inicio} {y}h{x - inicio}v1h-{x - inicio}z")
            else:
                x += 1
    return len(matriz), "".join(tramos)


def datos() -> str:
    """`datos.json` tal cual: la presentación lo lee de un <script> embebido."""
    return (AQUI / "datos.json").read_text(encoding="utf-8")


def resolver(marca: re.Match[str]) -> str:
    tipo, valor = marca.group(1), marca.group(2)
    if tipo == "FUENTE":
        return fuente(valor)
    if tipo == "QR_LADO":
        return str(qr(valor)[0])
    if tipo == "QR_TRAZO":
        return qr(valor)[1]
    if tipo == "IMG":
        return imagen(valor)
    raise ValueError(f"marca desconocida: {tipo}")


def main() -> None:
    plantilla = (AQUI / "plantilla.html").read_text(encoding="utf-8")
    salida = plantilla.replace("{{DATOS}}", datos())
    salida = re.sub(r"\{\{(FUENTE|QR_LADO|QR_TRAZO|IMG):([^}]+)\}\}", resolver, salida)
    destino = AQUI / "index.html"
    destino.write_text(salida, encoding="utf-8")
    print(f"{destino.name}: {len(salida) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
