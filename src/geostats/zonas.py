"""Recortes geográficos de la base ATUS.

Uso:
    uv run zona-atus                 # escribe el parquet de la ZMM
    uv run zona-atus --geo           # además el GeoParquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from geostats import rutas

# Zona Metropolitana de Monterrey según el Sistema Urbano Nacional
# (CONAPO-SEDATU-INEGI): 18 municipios de Nuevo León. Las claves son CVE_MUN
# de 5 dígitos y los nombres están tomados literalmente de tc_municipio.csv.
#
# Estos 18 son, además, los únicos municipios de Nuevo León que aparecen en
# ATUS: la cobertura estatal de la encuesta coincide exactamente con la zona
# metropolitana, así que filtrar por EDO == 19 da el mismo resultado. Se deja
# la lista explícita para que el recorte no dependa de esa coincidencia.
ZMM_MONTERREY: dict[str, str] = {
    "19001": "Abasolo",
    "19006": "Apodaca",
    "19009": "Cadereyta Jiménez",
    "19010": "El Carmen",
    "19012": "Ciénega de Flores",
    "19018": "García",
    "19019": "San Pedro Garza García",
    "19021": "General Escobedo",
    "19025": "General Zuazua",
    "19026": "Guadalupe",
    "19031": "Juárez",
    "19039": "Monterrey",
    "19041": "Pesquería",
    "19045": "Salinas Victoria",
    "19046": "San Nicolás de los Garza",
    "19047": "Hidalgo",
    "19048": "Santa Catarina",
    "19049": "Santiago",
}


def filtrar(datos: pd.DataFrame, zona: dict[str, str] = ZMM_MONTERREY) -> pd.DataFrame:
    """Recorta a los municipios de la zona y agrega su nombre."""
    faltantes = set(zona) - set(datos["CVE_MUN"].unique())
    if faltantes:
        nombres = sorted(zona[c] for c in faltantes)
        raise ValueError(f"Municipios de la zona ausentes en los datos: {nombres}")

    recorte = datos[datos["CVE_MUN"].isin(zona)].copy()
    recorte.insert(
        recorte.columns.get_loc("CVE_MUN") + 1,
        "NOM_MUN",
        recorte["CVE_MUN"].map(zona).astype("string"),
    )
    return recorte.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=rutas.ATUS_GEORREFERENCIADO)
    parser.add_argument("--salida", type=Path, default=rutas.ATUS_ZMM)
    parser.add_argument(
        "--geo", action="store_true", help="además escribe el GeoParquet"
    )
    argumentos = parser.parse_args()

    completo = pd.read_parquet(argumentos.entrada)
    zmm = filtrar(completo)

    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    zmm.to_parquet(argumentos.salida, engine="pyarrow", compression="zstd", index=False)

    print(
        f"Zona Metropolitana de Monterrey: {len(zmm):,} registros "
        f"({len(zmm) / len(completo):.1%} del total nacional), "
        f"{zmm.CVE_MUN.nunique()} municipios"
    )
    print(f"{argumentos.salida.relative_to(rutas.RAIZ)} "
          f"({argumentos.salida.stat().st_size / 1024**2:.1f} MB)")

    if argumentos.geo:
        from geostats.consolidar import escribir_geoparquet

        escribir_geoparquet(zmm, rutas.ATUS_ZMM_GEO)
        print(f"{rutas.ATUS_ZMM_GEO.relative_to(rutas.RAIZ)} "
              f"({rutas.ATUS_ZMM_GEO.stat().st_size / 1024**2:.1f} MB)")


if __name__ == "__main__":
    main()
