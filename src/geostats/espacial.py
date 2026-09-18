"""Unidades espaciales para el análisis y el modelado de la ZMM.

La rejilla hexagonal vive aquí y no en un notebook porque el modelo predictivo
tiene que usar **exactamente la misma partición** que el análisis espacial: si
cada uno construyera la suya, los resultados no serían comparables.

Uso:
    from geostats import espacial, rutas
    g = gpd.read_parquet(rutas.ATUS_ZMM_LIMPIO_GEO).to_crs(espacial.UTM_ZMM)
    H = espacial.rejilla_hexagonal(g.total_bounds, lado=500)
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

# UTM zona 14 Norte (EPSG:32614). Monterrey está en -100.3° de longitud, dentro
# de la franja -102° a -96° de la zona 14. Las coordenadas del INEGI vienen en
# WGS 84 (grados), donde una distancia no significa lo mismo en los dos ejes:
# cualquier cálculo métrico exige proyectar primero.
UTM_ZMM = 32614


def rejilla_hexagonal(
    bounds: np.ndarray, lado: float, crs: int = UTM_ZMM
) -> gpd.GeoDataFrame:
    """Hexágonos regulares de lado `lado` (en metros) que cubren `bounds`.

    Orientación *flat-top*: un vértice a la izquierda y otro a la derecha. Las
    columnas impares van desplazadas media altura para que los hexágonos
    encajen sin huecos. El área de cada celda es (3√3/2)·lado², así que un lado
    de 500 m da 0.65 km², comparable a un AGEB urbano.

    `bounds` es `(xmin, ymin, xmax, ymax)` en la misma proyección que `crs`,
    normalmente `GeoDataFrame.total_bounds`.
    """
    xmin, ymin, xmax, ymax = bounds
    alto = np.sqrt(3) * lado
    paso_x = 1.5 * lado
    columnas = int(np.ceil((xmax - xmin) / paso_x)) + 2
    filas = int(np.ceil((ymax - ymin) / alto)) + 2
    angulos = np.deg2rad(np.arange(0, 360, 60))

    poligonos = []
    claves = []
    for i in range(columnas):
        cx = xmin + i * paso_x
        desfase = alto / 2 if i % 2 else 0.0
        for j in range(filas):
            cy = ymin + j * alto + desfase
            vertices = zip(cx + lado * np.cos(angulos), cy + lado * np.sin(angulos))
            poligonos.append(Polygon(vertices))
            claves.append(f"{i}_{j}")

    return gpd.GeoDataFrame({"hex": claves}, geometry=poligonos, crs=crs)


def celdas(
    puntos: gpd.GeoDataFrame, lado: float = 500
) -> tuple[gpd.GeoDataFrame, "weights.W"]:
    """Las celdas de análisis de la ZMM y su matriz de contigüidad.

    Reproduce la partición de `analisis_espacial.qmd`: rejilla hexagonal sobre
    los puntos, solo celdas con al menos un accidente, y sin islas (celdas
    cuyas vecinas no tienen ninguno). Devuelve la rejilla con el índice
    `hex`, una columna `n` con el total de accidentes, y la matriz de pesos
    de contigüidad estandarizada por fila.

    `puntos` debe venir ya en `UTM_ZMM`. Cada punto se asigna a la celda que
    lo contiene; los que caen exactamente sobre una arista se pierden (uno en
    toda la base).
    """
    from libpysal import weights

    rejilla = rejilla_hexagonal(puntos.total_bounds, lado=lado)
    union = gpd.sjoin(puntos[["geometry"]], rejilla, predicate="within", how="inner")
    conteo = union.groupby("hex").size().rename("n")
    rejilla = rejilla.set_index("hex").join(conteo, how="inner").reset_index()

    w0 = weights.Queen.from_dataframe(rejilla, use_index=False, silence_warnings=True)
    rejilla = rejilla.drop(index=w0.islands).reset_index(drop=True)
    w = weights.Queen.from_dataframe(rejilla, use_index=False, silence_warnings=True)
    w.transform = "r"
    return rejilla, w
