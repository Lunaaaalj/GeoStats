"""Consolida los CSV georreferenciados de ATUS (INEGI) en un solo Parquet.

Los archivos vienen uno por año en `data/raw/ATUS_<año>/conjunto_de_datos/*.csv`.
El esquema es estable (49 columnas); a partir de 2022 el INEGI agregó una
columna `OID` que es solo un índice interno del shapefile y se descarta.

Uso:
    uv run consolidar-atus                # parquet tabular
    uv run consolidar-atus --geo          # además, GeoParquet con geometría
    uv run consolidar-atus --verificar    # contrasta el resultado con los .shp
"""

from __future__ import annotations

import argparse
import codecs
import re
from pathlib import Path

import pandas as pd

from geostats import rutas

# El .cpg del shapefile declara CP1252 y es correcto: en el rango 0x80-0x9F
# CP1252 tiene caracteres imprimibles (guiones y comillas tipográficas) que
# latin-1 convierte en caracteres de control. Son 719 caracteres en los seis
# años -- pocos, pero mal leídos en silencio.
#
# El problema es que 740 bytes del origen caen en los cinco huecos que CP1252
# no define. Este manejador los decodifica con semántica latin-1, así que se
# obtiene el texto correcto sin perder ningún byte (nada se vuelve U+FFFD).
#
# No usar chardet: sobre estos archivos devuelve CP874/TIS-620 con confianza
# 0.00, porque apenas ~1 de cada 250 bytes es no-ASCII.
ENCODING = "cp1252"
ERRORES = "cp1252_con_respaldo_latin1"


def _respaldo_latin1(error: UnicodeDecodeError):
    """Lee con latin-1 los cinco bytes que CP1252 deja sin definir."""
    crudo = error.object[error.start : error.end]
    return crudo.decode("latin-1"), error.end


codecs.register_error(ERRORES, _respaldo_latin1)

# Columnas presentes solo en algunos años y sin valor analítico.
COLUMNAS_DESCARTADAS = ["OID"]

COLUMNAS_TEXTO = ["ID", "CALLE1", "CALLE2", "CARRETERA"]
COLUMNAS_COORDENADA = ["LONGITUD", "LATITUD"]

# `ID` no identifica un accidente por sí solo: en 2019-2020 es un folio
# consecutivo por municipio (se repite ~269 mil veces) y desde 2021 es un
# identificador compuesto. La llave real necesita el año y el municipio.
LLAVE = ["ANIO", "EDO", "MPIO", "ID"]

# Los seis .prj declaran WGS84 geográfico.
CRS = "EPSG:4326"

PATRON_DIRECTORIO = re.compile(r"^ATUS_(\d{4})$")


def buscar_csv(crudos: Path = rutas.CRUDOS) -> dict[int, Path]:
    """Mapea año -> ruta del CSV georreferenciado de ese año."""
    encontrados: dict[int, Path] = {}
    for directorio in sorted(crudos.glob("ATUS_*")):
        coincidencia = PATRON_DIRECTORIO.match(directorio.name)
        if not coincidencia:
            continue
        csvs = list((directorio / "conjunto_de_datos").glob("*.csv"))
        if len(csvs) != 1:
            raise FileNotFoundError(
                f"{directorio.name}: se esperaba 1 CSV, se encontraron {len(csvs)}"
            )
        encontrados[int(coincidencia.group(1))] = csvs[0]
    if not encontrados:
        raise FileNotFoundError(f"No hay directorios ATUS_<año> en {crudos}")
    return encontrados


def leer_anio(ruta: Path, anio: int) -> pd.DataFrame:
    """Lee un CSV anual ya tipado y validado contra el año esperado."""
    datos = pd.read_csv(
        ruta,
        encoding=ENCODING,
        encoding_errors=ERRORES,
        dtype={columna: "string" for columna in COLUMNAS_TEXTO},
        low_memory=False,
    )
    datos = datos.drop(columns=COLUMNAS_DESCARTADAS, errors="ignore")

    # Todo lo demás son códigos de catálogo o conteos: nada excede int16.
    numericas = [
        columna
        for columna in datos.columns
        if columna not in COLUMNAS_TEXTO + COLUMNAS_COORDENADA
    ]
    datos[numericas] = datos[numericas].astype("int16")
    datos[COLUMNAS_COORDENADA] = datos[COLUMNAS_COORDENADA].astype("float64")

    discrepancias = datos.loc[datos["ANIO"] != anio, "ANIO"]
    if not discrepancias.empty:
        raise ValueError(
            f"{ruta.name}: {len(discrepancias)} filas con ANIO distinto de {anio} "
            f"(valores: {sorted(discrepancias.unique())})"
        )
    return datos


def consolidar(
    crudos: Path = rutas.CRUDOS,
    salida: Path = rutas.ATUS_GEORREFERENCIADO,
) -> pd.DataFrame:
    """Une todos los años en un DataFrame y lo escribe como Parquet."""
    partes = []
    for anio, ruta in sorted(buscar_csv(crudos).items()):
        datos = leer_anio(ruta, anio)
        print(f"  {anio}: {len(datos):>7,} filas  {len(datos.columns)} columnas")
        partes.append(datos)

    # Los años viejos no traen OID, así que el concat alinea por nombre y el
    # orden de columnas lo fija el primer año (el esquema base de 49).
    completo = pd.concat(partes, ignore_index=True)

    duplicados = completo.duplicated(LLAVE).sum()
    if duplicados:
        raise ValueError(f"{duplicados} filas duplicadas por {LLAVE}")

    # Clave geoestadística INEGI de 5 dígitos (2 de estado + 3 de municipio),
    # que es como se une con los shapefiles de marco geoestadístico.
    completo.insert(
        completo.columns.get_loc("MPIO") + 1,
        "CVE_MUN",
        completo["EDO"].astype(str).str.zfill(2)
        + completo["MPIO"].astype(str).str.zfill(3),
    )
    completo["CVE_MUN"] = completo["CVE_MUN"].astype("string")

    salida.parent.mkdir(parents=True, exist_ok=True)
    completo.to_parquet(salida, engine="pyarrow", compression="zstd", index=False)
    return completo


def escribir_geoparquet(
    completo: pd.DataFrame, salida: Path = rutas.ATUS_GEOPARQUET
) -> "gpd.GeoDataFrame":
    """Escribe el mismo contenido como GeoParquet, con geometría y CRS.

    La geometría se construye desde LONGITUD/LATITUD en vez de leer los .shp:
    `verificar_shp` comprueba que ambas coinciden exactamente, así que releer
    5 GB de shapefiles no aportaría ni un punto distinto.
    """
    import geopandas as gpd

    puntos = gpd.GeoDataFrame(
        completo,
        geometry=gpd.points_from_xy(completo["LONGITUD"], completo["LATITUD"]),
        crs=CRS,  # el .prj de los seis años declara WGS84
    )
    salida.parent.mkdir(parents=True, exist_ok=True)
    puntos.to_parquet(salida, compression="zstd", index=False)
    return puntos


def verificar_shp(crudos: Path = rutas.CRUDOS) -> pd.DataFrame:
    """Contrasta cada shapefile contra su CSV y reporta las diferencias.

    Existe para que la decisión de no consolidar los .shp sea auditable: si
    algún año dejara de coincidir, esto lo detecta.
    """
    import geopandas as gpd
    import numpy as np

    filas = []
    for anio, csv in sorted(buscar_csv(crudos).items()):
        shp = next(csv.parent.glob("*.shp"))
        forma = gpd.read_file(shp)
        tabla = leer_anio(csv, anio)

        forma["ID"] = forma["ID"].astype("string")
        for columna in ("ANIO", "EDO", "MPIO"):
            forma[columna] = forma[columna].astype("int16")

        unido = tabla.merge(
            forma[LLAVE + ["geometry"]], on=LLAVE, how="outer", indicator=True
        )
        emparejados = unido["_merge"] == "both"
        geo = gpd.GeoSeries(unido.loc[emparejados, "geometry"])
        desfase = np.maximum(
            (unido.loc[emparejados, "LONGITUD"] - geo.x).abs(),
            (unido.loc[emparejados, "LATITUD"] - geo.y).abs(),
        )
        filas.append({
            "anio": anio,
            "filas_csv": len(tabla),
            "filas_shp": len(forma),
            "solo_en_csv": int((unido["_merge"] == "left_only").sum()),
            "solo_en_shp": int((unido["_merge"] == "right_only").sum()),
            "desfase_max_grados": float(desfase.max()),
        })
    return pd.DataFrame(filas).set_index("anio")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crudos", type=Path, default=rutas.CRUDOS)
    parser.add_argument("--salida", type=Path, default=rutas.ATUS_GEORREFERENCIADO)
    parser.add_argument(
        "--geo", action="store_true",
        help="además escribe un GeoParquet con geometría de puntos y CRS",
    )
    parser.add_argument(
        "--verificar", action="store_true",
        help="contrasta los shapefiles contra los CSV y termina",
    )
    argumentos = parser.parse_args()

    if argumentos.verificar:
        print("Contrastando shapefiles contra CSV:")
        print(verificar_shp(argumentos.crudos).to_string())
        return

    print("Leyendo CSV anuales:")
    completo = consolidar(argumentos.crudos, argumentos.salida)

    mb_parquet = argumentos.salida.stat().st_size / 1024**2
    print(
        f"\n{len(completo):,} filas x {len(completo.columns)} columnas"
        f"\n{argumentos.salida.relative_to(rutas.RAIZ)} ({mb_parquet:.1f} MB)"
    )

    if argumentos.geo:
        escribir_geoparquet(completo)
        mb_geo = rutas.ATUS_GEOPARQUET.stat().st_size / 1024**2
        print(f"{rutas.ATUS_GEOPARQUET.relative_to(rutas.RAIZ)} ({mb_geo:.1f} MB)")


if __name__ == "__main__":
    main()
