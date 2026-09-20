"""Extrae de `processed/` las cifras que la presentación dibuja en vivo.

Escribe `datos.json`, que `construir.py` incrusta en el HTML. La presentación
no lee Parquet ni depende del entorno de Python: una vez construida es un
archivo suelto.

    uv run python docs/presentacion/datos.py
"""

from __future__ import annotations

import json
import pathlib
import re

import geopandas as gpd
import numpy as np
import pandas as pd

from geostats import espacial, rutas

AQUI = pathlib.Path(__file__).parent
LADO = 500.0


def por_celda(union: pd.DataFrame, mascara, orden) -> list[int]:
    """Conteo por celda de un subconjunto, alineado al orden de la rejilla."""
    s = union[mascara].groupby("hex").size()
    return s.reindex(orden, fill_value=0).astype(int).tolist()


def main() -> None:
    g = gpd.read_parquet(rutas.ATUS_ZMM_LIMPIO_GEO).to_crs(espacial.UTM_ZMM)
    rejilla, _ = espacial.celdas(g, lado=LADO)
    print(f"{len(rejilla):,} celdas")

    # Cada accidente a su celda. Se conserva el índice original para poder
    # arrastrar los atributos del accidente al agregado por celda.
    union = gpd.sjoin(
        g[["geometry", "ANIO", "TIPACCID", "MOTOCICLET", "BICICLETA",
           "hay_victimas", "NOM_MUN", "hora", "dia_semana"]],
        rejilla[["hex", "geometry"]],
        predicate="within", how="inner",
    )
    orden = rejilla["hex"]

    # --- posición en la retícula: el `hex` es "columna_fila" -----------------
    ij = orden.str.split("_", expand=True).astype(int)
    i, j = ij[0].to_numpy(), ij[1].to_numpy()

    capas = {"total": rejilla["n"].astype(int).tolist()}
    for anio in range(2019, 2025):
        capas[f"a{anio}"] = por_celda(union, union.ANIO == anio, orden)
    # TIPACCID: 2 atropellamiento, 10 colisión con motocicleta, 11 con ciclista
    capas["moto"] = por_celda(union, union.TIPACCID == 10, orden)
    capas["ciclista"] = por_celda(union, union.TIPACCID == 11, orden)
    capas["peaton"] = por_celda(union, union.TIPACCID == 2, orden)
    capas["victimas"] = por_celda(union, union.hay_victimas.fillna(False), orden)

    # --- municipio dominante de cada celda -----------------------------------
    dominante = union.groupby("hex").NOM_MUN.agg(
        lambda s: s.value_counts().index[0]).reindex(orden)
    nombres = sorted(dominante.unique())
    indice_mun = {m: k for k, m in enumerate(nombres)}

    # --- el pronóstico 2027, tal como lo dejó el notebook --------------------
    pron = gpd.read_parquet(rutas.PRONOSTICO_2027_GEO).set_index("hex")
    # Por municipio: el observado de 2024 y la media a posteriori de 2027 (la
    # media de una suma es la suma de las medias; las medianas no se suman).
    por_mun = pron.groupby("municipio")[["y_2024", "lambda_media"]].sum()
    pron = pron.reindex(orden)
    capas["p2027"] = pron["lambda_med"].fillna(0).round().astype(int).tolist()
    capas["ptop5"] = (pron["p_top5"].fillna(0) * 100).round().astype(int).tolist()

    # --- hora × día ----------------------------------------------------------
    dias = list(g.dia_semana.cat.categories) if hasattr(g.dia_semana, "cat") \
        else list(pd.unique(g.dia_semana))
    tabla = (g.groupby(["dia_semana", "hora"], observed=True).size()
             .unstack(fill_value=0).reindex(index=dias, columns=range(24), fill_value=0))
    hora_dia = tabla.astype(int).to_numpy().tolist()

    # --- curva de concentración por cruce ------------------------------------
    conteo = g.groupby("id_punto_4d").size().sort_values(ascending=False).to_numpy()
    acum = np.cumsum(conteo) / conteo.sum()
    muestra = np.unique(np.concatenate([
        np.arange(0, 200),                                  # la cabeza, punto a punto
        np.geomspace(200, len(conteo) - 1, 160).astype(int),
    ]))
    lorenz = [[round(float(k + 1) / len(conteo) * 100, 4),
               round(float(acum[k]) * 100, 3)] for k in muestra]

    # --- series municipales ---------------------------------------------------
    serie = (g.groupby(["NOM_MUN", "ANIO"], observed=True).size()
             .unstack(fill_value=0).sort_values(2024, ascending=False))

    # --- cruces: posición en las mismas unidades que la rejilla --------------
    # El origen de la rejilla es la esquina inferior izquierda de los puntos,
    # así que basta dividir entre el lado para que todo comparta un solo plano.
    xmin, ymin = g.total_bounds[0], g.total_bounds[1]
    nodos = (g.groupby("id_punto_4d")
             .agg(n=("geometry", "size"),
                  x=("geometry", lambda s: s.iloc[0].x),
                  y=("geometry", lambda s: s.iloc[0].y),
                  # El mismo cruce se captura con nombres distintos según
                  # el parte; se queda el que más veces aparece, no el primero.
                  c1=("calle1_norm", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
                  c2=("calle2_norm", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
                  mun=("NOM_MUN", "first"))
             .sort_values("n", ascending=False))
    cabeza = nodos.head(600)
    cruces_xy = [[round((r.x - xmin) / LADO, 2), round((r.y - ymin) / LADO, 2), int(r.n)]
                 for r in cabeza.itertuples()]
    def corto(calle: str) -> str:
        """Quita el genérico del nombre: en pantalla estorba y nadie lo dice."""
        return re.sub(r"^(Avenida|Calle|Calzada|Boulevard|Carretera|Prolongacion) ",
                      "", calle.title())

    cruces_top = [[f"{corto(r.c1)} × {corto(r.c2)}", r.mun, int(r.n)]
                  for r in nodos.head(10).itertuples()]

    # concentración por número de cruces, para la tabla
    conteo_cruce = nodos["n"].to_numpy()
    acum_cruce = np.cumsum(conteo_cruce) / conteo_cruce.sum()
    hitos = [[k, round(float(k) / len(conteo_cruce) * 100, 2),
              round(float(acum_cruce[k - 1]) * 100, 1)]
             for k in (50, 250, 1000, 5000)]

    # --- vialidades: los dos campos de calle cuentan igual -------------------
    calles = pd.concat([g.calle1_norm, g.calle2_norm]).dropna()
    vialidades = [[n.title(), int(v)] for n, v in calles.value_counts().head(8).items()]

    # --- corredores: cada avenida dibujada con sus propios cruces ------------
    # No hay geometría de calles en el repositorio, así que la avenida se
    # reconstruye con los cruces que la nombran: se ordenan a lo largo de su
    # eje principal (el primer componente de la nube de puntos) y se unen.
    corredores = []
    for nombre, _ in calles.value_counts().head(6).items():
        toca = g[(g.calle1_norm == nombre) | (g.calle2_norm == nombre)]
        cruces_via = (toca.groupby("id_punto_4d")
                      .agg(n=("geometry", "size"),
                           x=("geometry", lambda t: t.iloc[0].x),
                           y=("geometry", lambda t: t.iloc[0].y)))
        cruces_via = cruces_via[cruces_via.n >= 5]
        if len(cruces_via) < 3:
            continue
        xy = cruces_via[["x", "y"]].to_numpy()
        centro_via = xy.mean(axis=0)
        eje = np.linalg.svd(xy - centro_via, full_matrices=False)[2][0]
        orden_via = np.argsort((xy - centro_via) @ eje)
        corredores.append({
            "nombre": nombre.title(),
            "n": int(toca.shape[0]),
            "xy": [[round((xy[k, 0] - xmin) / LADO, 2),
                    round((xy[k, 1] - ymin) / LADO, 2),
                    int(cruces_via.n.iloc[k])] for k in orden_via],
        })

    # --- anillos: cuartiles de CELDAS por distancia al centroide --------------
    # Es el corte de `patrones_espaciales.qmd`: se agrupan celdas, no
    # accidentes, para que el % de víctimas y el conteo por celda se lean
    # sobre la misma unidad.
    centros = rejilla.geometry.centroid
    centro = np.array([g.geometry.x.mean(), g.geometry.y.mean()])
    d_celda = pd.Series(
        np.hypot(centros.x - centro[0], centros.y - centro[1]).to_numpy(),
        index=orden.to_numpy())
    grupo = pd.qcut(d_celda, 4, labels=[1, 2, 3, 4])
    victimas_celda = pd.Series(capas["victimas"], index=orden.to_numpy())
    total_celda = pd.Series(capas["total"], index=orden.to_numpy())
    anillos = []
    for k in (1, 2, 3, 4):
        m = grupo == k
        anillos.append([int(k),
                        round(float(victimas_celda[m].sum() / total_celda[m].sum()) * 100, 1),
                        int(round(total_celda[m].mean()))])

    # --- el país entero, en celdas de 0,1° -----------------------------------
    # No es un mapa de México con sus fronteras: es dónde están los accidentes
    # que ATUS registra. Lo que dibuja es el sistema urbano del país, con la
    # franja fronteriza y el centro marcados por su propia siniestralidad.
    nac = gpd.read_parquet(rutas.ATUS_GEOPARQUET, columns=["geometry"])
    PASO = 0.1
    ni = np.floor((nac.geometry.x.to_numpy() + 118) / PASO).astype(int)
    nj = np.floor((nac.geometry.y.to_numpy() - 14) / PASO).astype(int)
    cuenta = pd.DataFrame({"i": ni, "j": nj}).value_counts().reset_index(name="n")
    # Dónde cae la ZMM en esa misma retícula, para poder acercarse hasta ella.
    zmm = g.to_crs(4326)
    foco = [float(np.floor((zmm.geometry.x.mean() + 118) / PASO)),
            float(np.floor((zmm.geometry.y.mean() - 14) / PASO))]

    datos = {
        "rejilla": {"i": i.tolist(), "j": j.tolist()},
        "nacional": {"paso": PASO,
                     "i": cuenta.i.tolist(), "j": cuenta.j.tolist(),
                     "n": cuenta.n.tolist(), "foco": foco},
        "capas": capas,
        "municipios": {
            "nombres": nombres,
            "porCelda": [indice_mun[m] for m in dominante],
            "serie": {m: serie.loc[m].astype(int).tolist() for m in serie.index},
            "p2027": {m: [int(r.y_2024), int(round(r.lambda_media))]
                      for m, r in por_mun.sort_values("y_2024", ascending=False).iterrows()},
        },
        "horaDia": {"dias": [str(d)[:3] for d in dias], "tabla": hora_dia},
        "lorenz": lorenz,
        "totalPorAnio": g.groupby("ANIO").size().astype(int).tolist(),
        "cruces": {"xy": cruces_xy, "top": cruces_top, "hitos": hitos,
                   "nodos": int(len(nodos))},
        "vialidades": vialidades,
        "corredores": corredores,
        "anillos": anillos,
        # Perfiles de cruce: salen del k-medias de `patrones_espaciales.qmd`.
        # Se copian porque reproducir el agrupamiento aquí costaría minutos y
        # el resultado es estable (99,8 % de los cruces conserva su tipo).
        # Los siete rasgos son los que entraron al modelo, en el mismo orden;
        # `silueta` documenta que k = 4 no es el óptimo del índice.
        "agrupamiento": {
            "universo": 2302, "accidentes": 207207, "porcentaje": 54.6, "minimo": 30,
            "rasgos": [
                ["madrugada", "De madrugada", "entre las 00 y las 05 h"],
                ["finde", "En fin de semana", "sábado o domingo"],
                ["moto", "Con motocicleta", "colisión con moto"],
                ["vulnerable", "Con peatón o ciclista", "atropellamiento o ciclista"],
                ["objetoFijo", "Contra objeto fijo", "poste, muro, árbol, auto estacionado"],
                ["victimas", "Con víctimas", "alguien lesionado o muerto"],
                ["vehiculos", "Vehículos por choque", "promedio de vehículos involucrados"],
            ],
            "silueta": [[2, 0.284], [3, 0.280], [4, 0.206], [5, 0.216],
                        [6, 0.184], [7, 0.181], [8, 0.187]],
            "estabilidad": 99.8,
        },
        "tipos": [
            {"nombre": "Alto flujo, daños materiales", "cruces": 1163, "accidentes": 123869,
             "porCruce": 107, "madrugada": 5.7, "finde": 17.3, "moto": 3.6,
             "vulnerable": 1.3, "objetoFijo": 8.4, "victimas": 2.8, "vehiculos": 1.97,
             "km": 5.8},
            {"nombre": "Corredor de motocicleta", "cruces": 525, "accidentes": 36732,
             "porCruce": 70, "madrugada": 7.8, "finde": 28.7, "moto": 9.6,
             "vulnerable": 2.0, "objetoFijo": 6.6, "victimas": 5.5, "vehiculos": 1.95,
             "km": 8.9},
            {"nombre": "Pérdida de control nocturna", "cruces": 338, "accidentes": 29471,
             "porCruce": 87, "madrugada": 14.4, "finde": 26.2, "moto": 3.9,
             "vulnerable": 1.4, "objetoFijo": 25.4, "victimas": 4.9, "vehiculos": 1.77,
             "km": 8.8},
            {"nombre": "Exposición de peatón y ciclista", "cruces": 276, "accidentes": 17135,
             "porCruce": 62, "madrugada": 8.1, "finde": 27.2, "moto": 8.9,
             "vulnerable": 7.7, "objetoFijo": 8.3, "victimas": 13.2, "vehiculos": 1.88,
             "km": 6.7},
        ],
    }

    salida = AQUI / "datos.json"
    salida.write_text(json.dumps(datos, separators=(",", ":"), ensure_ascii=False),
                      encoding="utf-8")
    print(f"datos.json: {salida.stat().st_size / 1024:.0f} KB")
    print("  capas:", ", ".join(capas))
    print("  máximo hora×día:", max(max(f) for f in hora_dia))
    print(f"  país: {len(cuenta):,} celdas de {PASO}°, foco ZMM en {foco}")
    for cr in corredores:
        print(f"  corredor {cr['nombre'][:28]:28s} {len(cr['xy']):3d} cruces")


if __name__ == "__main__":
    main()
