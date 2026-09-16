"""Limpieza de la base ATUS recortada a la Zona Metropolitana de Monterrey.

Principio de la etapa: **nunca borra filas y nunca imputa**. Solo agrega
columnas derivadas y banderas, y deja intactas las del INEGI. Así el hallazgo
MNAR de `notebooks/calidad_datos.qmd` (el faltante depende de la gravedad,
así que `dropna()` sesga contra los accidentes fatales) queda impedido por la
arquitectura y no por acordarse.

Convención de nombres:
    MAYÚSCULAS  tal como llegó del INEGI. Se conservan sin tocar, incluidos
                los códigos centinela: distinguen «se fugó» de «se ignora»,
                que son mecanismos distintos.
    minúsculas  construido por este repo.

    Excepción: `CVE_MUN` y `NOM_MUN` son derivadas pero van en mayúsculas,
    porque siguen la nomenclatura de claves geoestadísticas del propio INEGI.

Uso:
    uv run limpiar-atus              # data/processed/atus_zmm_limpio.parquet
    uv run limpiar-atus --geo        # además el GeoParquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from geostats import rutas, zonas

# Códigos centinela documentados en el diccionario del INEGI. El INEGI no usa
# nulos: la ausencia de información se codifica como un valor válido del
# catálogo, así que `isna()` no ve nada de esto en las columnas originales.
CENTINELAS: dict[str, dict[int, str]] = {
    "HORA": {99: "no especificado"},
    "MINUTOS": {99: "no especificado"},
    "DIA": {32: "no especificado"},
    "DIASEMANA": {8: "no especificado"},
    "SEXO": {1: "se fugó (sexo desconocido)"},
    "ALIENTO": {6: "se ignora"},
    "CINTURON": {9: "se ignora"},
    "EDAD": {0: "se fugó", 99: "no especificado"},
}

# Catálogos del INEGI. Los códigos que faltan en cada mapa son los centinelas
# de arriba, y se vuelven NA en la columna derivada.
SEXO = {2: "Hombre", 3: "Mujer"}
ALIENTO = {4: True, 5: False}
CINTURON = {7: True, 8: False}
DIA_SEMANA = {
    1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves",
    5: "Viernes", 6: "Sábado", 7: "Domingo",
}
GRAVEDAD = {1: "Fatal", 2: "No fatal", 3: "Solo daños"}

# `URBANA` y `SUBURBANA` son excluyentes y el campo que no aplica lleva 0, así
# que se colapsan en una sola categórica de cinco niveles.
URBANA = {1: "Intersección", 2: "No intersección"}
SUBURBANA = {1: "Camino rural", 2: "Carretera estatal", 3: "Otro camino"}

ORDEN_DIA = list(DIA_SEMANA.values())
ORDEN_GRAVEDAD = list(GRAVEDAD.values())
ORDEN_UBICACION = list(URBANA.values()) + list(SUBURBANA.values())

VEHICULOS = [
    "AUTOMOVIL", "CAMPASAJ", "MICROBUS", "PASCAMION", "OMNIBUS", "TRANVIA",
    "CAMIONETA", "CAMION", "TRACTOR", "FERROCARRI", "MOTOCICLET",
    "BICICLETA", "OTROVEHIC",
]
MUERTOS = ["CONDMUERTO", "PASAMUERTO", "PEATMUERTO", "CICLMUERTO", "OTROMUERTO"]
HERIDOS = ["CONDHERIDO", "PASAHERIDO", "PEATHERIDO", "CICLHERIDO", "OTROHERIDO"]

COLUMNAS_TEXTO = ["CALLE1", "CALLE2", "CARRETERA"]

LLAVE = ["ANIO", "EDO", "MPIO", "ID"]

# Redondeo del identificador de punto con tolerancia. A la latitud de la ZMM
# (25.7 N) cuatro decimales son 11.1 m en latitud y 10.0 m en longitud: cabe
# holgado dentro de un mismo cruce. Con tres decimales serían 111 y 100 m, y la
# manzana en Monterrey mide ~100 m, así que fusionaría cruces contiguos.
DECIMALES_TOLERANCIA = 4

# Un punto con tres decimales o menos trae ~110 m de error y no sirve a escala
# de intersección.
DECIMALES_PRECISION_BAJA = 3


def _sin_centinela(columna: pd.Series, codigos: dict) -> pd.Series:
    """Enmascara como NA los códigos centinela del campo."""
    return columna.mask(columna.isin(list(codigos)))


def _normalizar_texto(columna: pd.Series) -> pd.Series:
    """Versión comparable de un nombre de vialidad, para contar y unir.

    Recorta, colapsa espacios internos, sube a mayúsculas y quita acentos. La
    columna original se conserva intacta porque los acentos son parte del
    nombre real y quitarlos ahí sería irreversible.

    Ojo: NFKD descompone `Ñ` en `N` + tilde combinante, así que quitar las
    marcas convierte `CAÑADA` en `CANADA`. Para emparejar es lo deseable, pero
    es una fusión real y por eso solo ocurre en la columna derivada.
    """
    limpio = (
        columna.str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.upper()
        .str.normalize("NFKD")
        .str.replace("[̀-ͯ]", "", regex=True)
    )
    # Una cadena vacía o de puros espacios es información ausente, no un nombre.
    return limpio.mask(limpio == "", pd.NA)


def _fecha(datos: pd.DataFrame) -> pd.Series:
    """Fecha del accidente; NaT donde no se puede construir.

    Dos casos caen en NaT y los dos importan: el centinela `DIA = 32` y las
    fechas imposibles (un 30 de febrero). `diagnostico` los cuenta por separado
    para que ninguno pase en silencio.

    No se construye una marca de tiempo completa a propósito: `MINUTOS` tiene
    preferencia de dígito severa (el 0 y el 30 concentran la quinta parte de la
    base), así que un timestamp afirmaría una resolución que el dato no tiene.
    """
    partes = datos[["ANIO", "MES", "DIA"]].astype("int64")
    partes.columns = ["year", "month", "day"]
    return pd.to_datetime(partes, errors="coerce")


def _id_punto(datos: pd.DataFrame, decimales: int | None = None) -> pd.Series:
    """Identificador legible y estable de la coordenada: `"lon,lat"`.

    El 72.3 % de los accidentes de la ZMM comparte coordenada exacta con otro
    porque el INEGI reutiliza el nodo de la intersección: el par exacto ya *es*
    el nodo. Se usa una cadena y no un código de `factorize` para que el
    identificador no cambie entre corridas y se pueda leer de vuelta.

    Sin `decimales`, la cadena sale de `str(float)`, que es la representación
    más corta que reconstruye el mismo float: el identificador es exacto sin
    tener que saber de antemano cuántos decimales trae el dato. Eso importa:
    estas coordenadas llegan con **hasta ocho** decimales, y formatearlas a
    seis fusiona 8,115 puntos distintos sin avisar. `validar` lo comprueba en
    cada corrida.
    """
    lon, lat = datos["LONGITUD"], datos["LATITUD"]
    if decimales is None:
        return (lon.astype(str) + "," + lat.astype(str)).astype("string")
    formato = f"{{:.{decimales}f}}".format
    return (
        lon.round(decimales).map(formato) + "," + lat.round(decimales).map(formato)
    ).astype("string")


def _precision_baja(datos: pd.DataFrame) -> pd.Series:
    """Marca los puntos geocodificados con tres decimales o menos.

    Se exige que **ambos** ejes sean gruesos, y los datos confirman por qué:
    866 registros tienen la longitud con tres decimales o menos y 1,028 tienen
    la latitud, pero solo **3** tienen las dos. Si fueran independientes se
    esperarían 2.3, o sea que la coincidencia de los dos ejes no aporta señal
    por encima del azar: en la ZMM prácticamente no hay coordenadas realmente
    burdas, solo floats cuya representación resulta corta.

    Por eso el hallazgo 11 de `calidad_datos.qmd` («866 registros con <=3
    decimales») sobreestima el problema: contaba un solo eje.

    `np.isclose` va con `rtol=0`: su tolerancia relativa por omisión sobre
    valores de magnitud ~100 sería de 1e-3 y daría verdadero para todo.
    """
    baja = []
    for eje in ("LONGITUD", "LATITUD"):
        valores = datos[eje].to_numpy()
        redondeado = np.round(valores, DECIMALES_PRECISION_BAJA)
        baja.append(np.isclose(valores, redondeado, rtol=0, atol=1e-9))
    return pd.Series(baja[0] & baja[1], index=datos.index)


def limpiar(datos: pd.DataFrame) -> pd.DataFrame:
    """Agrega las columnas derivadas. No borra filas, no imputa, no muta."""
    d = datos.copy()

    # --- Tiempo -----------------------------------------------------------
    d["fecha"] = _fecha(d)
    d["hora"] = _sin_centinela(d["HORA"], CENTINELAS["HORA"]).astype("Int8")
    d["dia_semana"] = pd.Categorical(
        _sin_centinela(d["DIASEMANA"], CENTINELAS["DIASEMANA"]).map(DIA_SEMANA),
        categories=ORDEN_DIA, ordered=True,
    )

    # --- Conductor presunto responsable -----------------------------------
    # `SEXO = 1` y `EDAD = 0` marcan exactamente los mismos registros: cuando
    # el conductor se fuga no hay a quién preguntarle la edad. La fuga es una
    # variable con significado propio, hoy escondida dentro de dos catálogos.
    d["se_fugo"] = d["SEXO"] == 1
    d["sexo_conductor"] = pd.Categorical(
        _sin_centinela(d["SEXO"], CENTINELAS["SEXO"]).map(SEXO),
        categories=list(SEXO.values()),
    )
    d["edad"] = _sin_centinela(d["EDAD"], CENTINELAS["EDAD"]).astype("Int16")
    d["aliento_alcoholico"] = (
        _sin_centinela(d["ALIENTO"], CENTINELAS["ALIENTO"])
        .map(ALIENTO)
        .astype("boolean")
    )
    d["cinturon"] = (
        _sin_centinela(d["CINTURON"], CENTINELAS["CINTURON"])
        .map(CINTURON)
        .astype("boolean")
    )

    # --- Ubicación y accidente --------------------------------------------
    d["ubicacion"] = pd.Categorical(
        d["URBANA"].map(URBANA).fillna(d["SUBURBANA"].map(SUBURBANA)),
        categories=ORDEN_UBICACION,
    )
    d["en_interseccion"] = d["URBANA"] == 1
    d["n_vehiculos"] = d[VEHICULOS].sum(axis=1).astype("int16")
    d["gravedad"] = pd.Categorical(
        d["CLASE"].map(GRAVEDAD), categories=ORDEN_GRAVEDAD, ordered=True
    )
    d["hay_victimas"] = d["CLASE"].isin([1, 2])

    # --- Vialidades --------------------------------------------------------
    for columna in COLUMNAS_TEXTO:
        d[f"{columna.lower()}_norm"] = _normalizar_texto(d[columna])
    # Una intersección tiene dos vialidades por definición, así que aquí el
    # hueco es faltante real y no estructural.
    d["falta_calle2"] = d["en_interseccion"] & d["calle2_norm"].isna()

    # --- Coordenadas -------------------------------------------------------
    d["id_punto"] = _id_punto(d)
    d[f"id_punto_{DECIMALES_TOLERANCIA}d"] = _id_punto(d, DECIMALES_TOLERANCIA)
    d["precision_baja"] = _precision_baja(d)

    return d


def validar(limpio: pd.DataFrame, n_original: int) -> None:
    """Falla si alguna invariante se rompió. Recorre todas antes de lanzar.

    Las diez primeras son las de `calidad_datos.qmd`, que se verificaron con
    cero violaciones sobre la base sucia: si aparecen ahora, la limpieza rompió
    algo. Las demás comprueban que las derivadas dicen lo que prometen.

    Es específica de la ZMM: comprueba pertenencia a `zonas.ZMM_MONTERREY`.
    """
    edad_valida = limpio.loc[~limpio["EDAD"].isin(CENTINELAS["EDAD"]), "EDAD"]
    victimas = limpio["TOTMUERTOS"] + limpio["TOTHERIDOS"]

    fallas = {
        "TOTMUERTOS != suma de componentes":
            (limpio[MUERTOS].sum(axis=1) != limpio["TOTMUERTOS"]).sum(),
        "TOTHERIDOS != suma de componentes":
            (limpio[HERIDOS].sum(axis=1) != limpio["TOTHERIDOS"]).sum(),
        "CLASE=Fatal con cero muertos":
            ((limpio["CLASE"] == 1) & (limpio["TOTMUERTOS"] == 0)).sum(),
        "CLASE=Solo daños con víctimas":
            ((limpio["CLASE"] == 3) & (victimas > 0)).sum(),
        "URBANA y SUBURBANA marcadas a la vez":
            ((limpio["URBANA"] > 0) & (limpio["SUBURBANA"] > 0)).sum(),
        "Sin zona asignada":
            ((limpio["URBANA"] == 0) & (limpio["SUBURBANA"] == 0)).sum(),
        "Sin ningún vehículo involucrado": (limpio["n_vehiculos"] == 0).sum(),
        "EDAD válida fuera del rango 12-98": (~edad_valida.between(12, 98)).sum(),
        "Llave (ANIO, EDO, MPIO, ID) duplicada": limpio.duplicated(LLAVE).sum(),
        "Municipio fuera de la ZMM":
            (~limpio["CVE_MUN"].isin(zonas.ZMM_MONTERREY)).sum(),
        # La limpieza agrega columnas; jamás filas.
        "Se perdieron o inventaron filas": abs(len(limpio) - n_original),
        # Equivalencias documentadas en el diccionario de datos.
        "se_fugo no coincide con EDAD=0":
            (limpio["se_fugo"] != (limpio["EDAD"] == 0)).sum(),
        "hay_victimas no coincide con el conteo de víctimas":
            (limpio["hay_victimas"] != (victimas > 0)).sum(),
        "ubicacion sin asignar": limpio["ubicacion"].isna().sum(),
        "gravedad sin asignar": limpio["gravedad"].isna().sum(),
        # Un `id_punto` con menos valores que pares de coordenadas significa
        # que el formato está fusionando puntos distintos en silencio.
        "id_punto no distingue coordenadas distintas": abs(
            limpio.groupby(["LONGITUD", "LATITUD"]).ngroups
            - limpio["id_punto"].nunique()
        ),
    }

    # Cada derivada debe estar en NA exactamente donde su original trae un
    # centinela: ni una fila más, ni una menos.
    for derivada, original in [
        ("hora", "HORA"), ("dia_semana", "DIASEMANA"), ("edad", "EDAD"),
        ("sexo_conductor", "SEXO"), ("aliento_alcoholico", "ALIENTO"),
        ("cinturon", "CINTURON"),
    ]:
        esperado = limpio[original].isin(list(CENTINELAS[original]))
        observado = pd.Series(pd.isna(limpio[derivada]), index=limpio.index)
        fallas[f"{derivada}: NA no corresponde a los centinelas de {original}"] = (
            observado != esperado
        ).sum()

    rotas = {nombre: int(n) for nombre, n in fallas.items() if n}
    if rotas:
        detalle = "\n".join(f"  {nombre}: {n:,}" for nombre, n in rotas.items())
        raise ValueError(f"La limpieza rompió {len(rotas)} invariante(s):\n{detalle}")


def diagnostico(limpio: pd.DataFrame) -> dict[str, int | float]:
    """Lo que hay que mirar, no lo que hay que reprobar.

    Nada de esto es un error: son cifras que cambian la lectura del análisis y
    que conviene ver impresas en cada corrida.
    """
    n = len(limpio)
    sin_fecha = limpio["fecha"].isna()
    centinela_dia = limpio["DIA"] == 32

    # `DIASEMANA` viene del INEGI y `fecha` se calcula: si discrepan, uno de los
    # dos está mal y hay que saberlo.
    comparables = limpio["fecha"].notna() & limpio["dia_semana"].notna()
    dia_calculado = limpio.loc[comparables, "fecha"].dt.dayofweek.map(
        dict(enumerate(ORDEN_DIA))
    )
    discrepancia_dia = (
        dia_calculado.to_numpy()
        != limpio.loc[comparables, "dia_semana"].astype("object").to_numpy()
    ).sum()

    puntos = limpio["id_punto"].value_counts()
    columna_tolerancia = f"id_punto_{DECIMALES_TOLERANCIA}d"

    texto_cambiado = sum(
        int((limpio[c].fillna("") != limpio[f"{c.lower()}_norm"].fillna("")).sum())
        for c in COLUMNAS_TEXTO
    )

    return {
        "filas": n,
        "columnas": len(limpio.columns),
        "fecha NaT (total)": int(sin_fecha.sum()),
        "fecha NaT por centinela DIA=32": int((sin_fecha & centinela_dia).sum()),
        "fecha NaT por fecha imposible": int((sin_fecha & ~centinela_dia).sum()),
        "DIASEMANA discrepa del día real": int(discrepancia_dia),
        "coordenadas únicas": int(len(puntos)),
        "% de filas que comparten coordenada": round(
            float(puntos[puntos > 1].sum() / n * 100), 1
        ),
        f"coordenadas únicas a {DECIMALES_TOLERANCIA} decimales": int(
            limpio[columna_tolerancia].nunique()
        ),
        "precisión baja (<=3 decimales)": int(limpio["precision_baja"].sum()),
        "CALLE2 ausente en intersección": int(limpio["falta_calle2"].sum()),
        "valores de texto que cambiaron al normalizar": texto_cambiado,
    }


def tasa_captura(datos: pd.DataFrame, campo: str = "CINTURON") -> pd.DataFrame:
    """Porcentaje de registros con dato real en `campo`, por municipio y año.

    Existe porque el faltante de `CINTURON`, `ALIENTO` y `EDAD` mide práctica
    administrativa y no conducta vial: va de 10.4 % en San Pedro a 100 % en
    Monterrey, y Guadalupe salta de 20.3 % a 96.8 % en un solo año. Cualquier
    comparación entre municipios o entre años tiene que reportarse junto a esta
    tabla.

    No es una columna del artefacto a propósito: es un agregado, y pegado a
    cada renglón dejaría de significar lo que dice en cuanto alguien filtre.
    """
    if campo not in CENTINELAS:
        raise ValueError(f"{campo} no tiene centinelas documentados")
    capturado = ~datos[campo].isin(list(CENTINELAS[campo]))
    etiqueta = "NOM_MUN" if "NOM_MUN" in datos.columns else "CVE_MUN"
    tabla = capturado.groupby([datos[etiqueta], datos["ANIO"]]).mean() * 100
    return tabla.unstack().round(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=rutas.ATUS_ZMM)
    parser.add_argument("--salida", type=Path, default=rutas.ATUS_ZMM_LIMPIO)
    parser.add_argument(
        "--geo", action="store_true", help="además escribe el GeoParquet"
    )
    argumentos = parser.parse_args()

    datos = pd.read_parquet(argumentos.entrada)
    limpio = limpiar(datos)
    validar(limpio, n_original=len(datos))

    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    limpio.to_parquet(
        argumentos.salida, engine="pyarrow", compression="zstd", index=False
    )

    print(f"{len(datos.columns)} columnas de entrada -> {len(limpio.columns)} de "
          f"salida ({len(limpio.columns) - len(datos.columns)} derivadas)\n")
    for nombre, valor in diagnostico(limpio).items():
        print(f"  {nombre:<48} {valor:>12,}")
    print(f"\n{argumentos.salida.relative_to(rutas.RAIZ)} "
          f"({argumentos.salida.stat().st_size / 1024**2:.1f} MB)")

    if argumentos.geo:
        from geostats.consolidar import escribir_geoparquet

        escribir_geoparquet(limpio, rutas.ATUS_ZMM_LIMPIO_GEO)
        print(f"{rutas.ATUS_ZMM_LIMPIO_GEO.relative_to(rutas.RAIZ)} "
              f"({rutas.ATUS_ZMM_LIMPIO_GEO.stat().st_size / 1024**2:.1f} MB)")


if __name__ == "__main__":
    main()
