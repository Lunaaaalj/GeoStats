"""Genera `relieve_3d.html`, el prototipo de relieve hexagonal de la ZMM.

Prototipo, no producto: sirve para decidir si el 3D entra a la presentación.
Los datos se incrustan en el HTML (no se cargan por `fetch`) para que el
archivo funcione al abrirlo desde el disco, sin servidor.

    uv run python docs/prototipo_3d/construir.py

Fuentes:
  data/processed/pronostico_2027_geo.parquet   (lo produce pronostico_2027.qmd)
  docs/presentacion/vialidades_zmm.json        (contexto vial, ya en EPSG:4326)
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np

from geostats import rutas

AQUI = Path(__file__).parent
PLANTILLA = AQUI / "plantilla.html"
SALIDA = AQUI / "relieve_3d.html"
VIALIDADES = rutas.RAIZ / "docs" / "presentacion" / "vialidades_zmm.json"


def datos() -> dict:
    g = gpd.read_parquet(rutas.PRONOSTICO_2027_GEO).to_crs(4326)

    # Riesgo relativo al propio municipio. Como lambda_med = exp(b0 + m_j + u_i)
    # y (b0 + m_j) es constante dentro de un municipio, dividir entre la media
    # geométrica municipal deja exactamente exp(u_i - media_j(u)): el perfil de
    # la celda, limpio del régimen de reporte de su municipio.
    g["log_lambda"] = np.log(g.lambda_med)
    media_mun = g.groupby("municipio").log_lambda.transform("mean")
    g["ratio"] = np.exp(g.log_lambda - media_mun)

    municipios = sorted(g.municipio.unique())
    indice = {m: i for i, m in enumerate(municipios)}

    celdas = []
    for fila in g.itertuples():
        anillo = [[round(x, 5), round(y, 5)] for x, y in fila.geometry.exterior.coords[:-1]]
        celdas.append({
            "p": anillo,
            "h": fila.hex,
            "m": indice[fila.municipio],
            "y": int(fila.y_2024),
            "l": round(fila.lambda_med, 2),
            "r": round(fila.ratio, 3),
            "a": int(fila.pred_q05),
            "b": int(fila.pred_q95),
            "t": round(fila.p_top5, 2),
        })

    vias = json.loads(VIALIDADES.read_text(encoding="utf-8"))["vias"]
    xmin, ymin, xmax, ymax = g.total_bounds
    return {
        "celdas": celdas,
        "municipios": municipios,
        "vias": [v[1] for v in vias],
        "centro": [round((xmin + xmax) / 2, 5), round((ymin + ymax) / 2, 5)],
    }


def main() -> None:
    carga = datos()
    html = PLANTILLA.read_text(encoding="utf-8").replace(
        "/*{{DATOS}}*/", json.dumps(carga, separators=(",", ":"), ensure_ascii=False)
    )
    SALIDA.write_text(html, encoding="utf-8")
    n = len(carga["celdas"])
    print(f"{SALIDA.relative_to(rutas.RAIZ)}: {n:,} celdas, {SALIDA.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
