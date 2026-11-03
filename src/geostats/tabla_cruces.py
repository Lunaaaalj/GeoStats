"""Tabla de cruces de la ZMM en Excel: hechos de tránsito, defunciones y peatones.

Una fila por cruce, con las mismas definiciones que `notebooks/cruces_peatones.qmd`:

- Un cruce es un nodo `id_punto_4d` (10 m de tolerancia) cuya ubicación más
  frecuente es «Intersección». Su nombre es el par de vialidades que más veces
  aparece en sus partes.
- Hecho con peatón: atropellamiento (`TIPACCID == 2`) o algún peatón muerto.
- Hecho con ciclista: colisión con ciclista (`TIPACCID == 11`) o algún ciclista
  muerto.

Los rankings usan el método «min»: los empates comparten el lugar más alto,
como en una tabla deportiva.

Uso:
    uv run tabla-cruces            # processed/atus_zmm_limpio.parquet -> docs/cruces_zmm.xlsx
"""

from __future__ import annotations

import argparse
import re

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from geostats import rutas
from geostats.limpieza import SEPARADOR_CRUCE

SALIDA = rutas.RAIZ / "docs" / "cruces_zmm.xlsx"

# Los mismos genéricos que quita `limpieza._homologar_vialidad`; «Carretera»,
# «Prolongación» y «Privada» se quedan, igual que en la columna homologada.
GENERICO = re.compile(r"^(AVENIDA|AVDA\.?|AVE\.?|AV\.?|CALLE|CALZADA|CALZ\.?|BOULEVARD|"
                      r"BLVD\.?|BLVR\.?)\s+", re.IGNORECASE)
MINUSCULAS = {"A", "De", "Del", "La", "Las", "Los", "Y", "El"}

# Identidad GeoStats: secciones en la rampa ordinal de azules, texto grafito,
# rejilla y subencabezados en gris claro.
AZUL = "005991"
RAMPA = (AZUL, "1B77B8")

TRANSPORTE_PUBLICO = ["CAMPASAJ", "MICROBUS", "PASCAMION", "OMNIBUS"]
TRANSPORTE_CARGA = ["CAMION", "TRACTOR"]
GRAFITO = "2C2C2C"
GRIS = "F2F2F2"
GRIS_TEXTO = "6B6B6B"  # rankings: secundarios frente a la cuenta


def calle_limpia(calle) -> str | None:
    """Quita el genérico («Avenida», «Calle»…) y normaliza mayúsculas.

    El genérico se queda si sin él el nombre empezaría con «de», «la», «los»…
    («Avenida de las Cumbres», no «De las Cumbres») o no tendría letras
    («Calle 5»), igual que en la homologación.
    """
    if not isinstance(calle, str) or not calle.strip():
        return None
    completo = re.sub(r"\s+", " ", calle.strip())
    nombre = GENERICO.sub("", completo)
    if nombre.split()[0].title() in MINUSCULAS or not re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{3}", nombre):
        nombre = completo
    palabras = nombre.title().split()
    return " ".join(p.lower() if p in MINUSCULAS and 0 < k < len(palabras) - 1 else p
                    for k, p in enumerate(palabras))


def nombres_de_cruce(d: pd.DataFrame) -> pd.DataFrame:
    """Nombre de cada nodo y si nombra dos calles distintas.

    El nombre sale de `vialidades_hom` (de `geostats.limpieza`): «A × B» cuando
    el parte nombra dos calles distintas y «A» sola cuando falta la calle 2,
    viene relleno («NINGUNO») o repite la calle 1. Votan primero los partes con
    dos calles: el par más frecuente gana aunque la mayoría del nodo nombre una
    sola, porque el parte que trae la segunda calle aporta lo que a los otros
    les falta. «A» sola queda solo si ningún parte del nodo trae un par. El par
    ya viene en orden alfabético, así que «A × B» y «B × A» votan juntos. Cada
    calle se muestra con su escritura más frecuente en toda la base.
    """
    if "vialidades_hom" not in d:
        raise KeyError("Falta vialidades_hom: vuelve a correr `uv run limpiar-atus`.")
    bonitas = pd.DataFrame({
        "k": pd.concat([d.calle1_hom, d.calle2_hom], ignore_index=True),
        "v": pd.concat([d.CALLE1.map(calle_limpia), d.CALLE2.map(calle_limpia)],
                       ignore_index=True),
    }).dropna()
    escritura = (bonitas.groupby(["k", "v"]).size().reset_index(name="n")
                 .sort_values(["k", "n", "v"], ascending=[True, False, True])
                 .drop_duplicates("k").set_index("k").v)

    def mas_frecuente(votos: pd.DataFrame) -> pd.Series:
        return (votos.groupby(["nodo", "v"]).size().reset_index(name="n")
                .sort_values(["nodo", "n", "v"], ascending=[True, False, True])
                .drop_duplicates("nodo").set_index("nodo").v)

    votos = pd.DataFrame({"nodo": d.id_punto_4d, "v": d.vialidades_hom}).dropna()
    par = votos.v.str.contains(SEPARADOR_CRUCE, regex=False)
    moda = mas_frecuente(votos[par]).combine_first(mas_frecuente(votos[~par]))
    nombre = moda.map(lambda v: " × ".join(escritura.get(c, c.title())
                                           for c in v.split(SEPARADOR_CRUCE)))
    return pd.DataFrame({
        "nombre": nombre,
        "interseccion": moda.str.contains(SEPARADOR_CRUCE, regex=False)
                            .map({True: "Sí", False: "No"}),
    })


def construir_tabla(d: pd.DataFrame) -> pd.DataFrame:
    d = d.assign(
        con_peaton=d.TIPACCID.eq(2) | d.PEATMUERTO.gt(0),
        con_ciclista=d.TIPACCID.eq(11) | d.CICLMUERTO.gt(0),
        con_moto=d.TIPACCID.eq(10) | d.MOTOCICLET.gt(0),
        con_publico=d[TRANSPORTE_PUBLICO].sum(axis=1).gt(0),
        con_carga=d[TRANSPORTE_CARGA].sum(axis=1).gt(0),
        defunciones_pc=d.PEATMUERTO + d.CICLMUERTO,
    )
    d["con_pc"] = d.con_peaton | d.con_ciclista
    # ATUS no separa las defunciones por tipo de vehículo: para motocicletas y
    # transporte se cuentan todas las defunciones de esos hechos.
    for k in ("moto", "publico", "carga"):
        d[f"def_{k}"] = d.TOTMUERTOS.where(d[f"con_{k}"], 0)
    g = d.groupby("id_punto_4d")
    nodos = pd.DataFrame({
        "hechos": g.size(),
        "defunciones": g.TOTMUERTOS.sum(),
        "hechos_peaton": g.con_peaton.sum(),
        "def_peaton": g.PEATMUERTO.sum(),
        "hechos_ciclista": g.con_ciclista.sum(),
        "def_ciclista": g.CICLMUERTO.sum(),
        "hechos_moto": g.con_moto.sum(),
        "def_moto": g.def_moto.sum(),
        "hechos_publico": g.con_publico.sum(),
        "def_publico": g.def_publico.sum(),
        "hechos_carga": g.con_carga.sum(),
        "def_carga": g.def_carga.sum(),
        "hechos_pc": g.con_pc.sum(),
        "defunciones_pc": g.defunciones_pc.sum(),
        "municipio": g.NOM_MUN.agg(lambda s: s.mode().iloc[0]),
        "ubicacion": g.ubicacion.agg(lambda s: s.mode().iloc[0]),
        "lat": g.LATITUD.median(),
        "lon": g.LONGITUD.median(),
    })
    cruces = nodos[nodos.ubicacion == "Intersección"].copy()
    nombres = nombres_de_cruce(d).reindex(cruces.index)
    cruces["nombre"] = nombres.nombre.fillna("Sin nombre")
    cruces["interseccion"] = nombres.interseccion.fillna("No")

    # Cada cuenta lleva su ranking en la columna «r_<cuenta>».
    for col in [c for c, _ in columnas_de(SECCIONES) if c.startswith("r_")]:
        base = col[2:]
        cruces[col] = cruces[base].rank(ascending=False, method="min").astype(int)
    cruces["maps"] = [f"https://www.google.com/maps?q={la:.6f},{lo:.6f}"
                      for la, lo in zip(cruces.lat, cruces.lon)]
    cruces["coordenadas"] = [f"{la:.6f}, {lo:.6f}" for la, lo in zip(cruces.lat, cruces.lon)]

    cruces = cruces.sort_values(["hechos", "defunciones", "nombre"],
                                ascending=[False, False, True])
    columnas = columnas_de(SECCIONES)
    return cruces[[c for c, _ in columnas]].set_axis([e for _, e in columnas], axis=1)


# Secciones de la hoja: (título, [(columna, encabezado), ...]). Cada sección de
# conteos lleva hechos de tránsito, su ranking y defunciones.
def _conteo(titulo: str, hechos: str, defunciones: str):
    return (titulo, [(hechos, "Hechos de tránsito"), (f"r_{hechos}", "Ranking"),
                     (defunciones, "Defunciones")])


SECCIONES = [
    ("Cruce", [("nombre", "Cruce"), ("interseccion", "Intersección (dos calles)")]),
    _conteo("Totales", "hechos", "defunciones"),
    _conteo("Solo peatones", "hechos_peaton", "def_peaton"),
    _conteo("Solo ciclistas", "hechos_ciclista", "def_ciclista"),
    _conteo("Peatones y/o ciclistas", "hechos_pc", "defunciones_pc"),
    _conteo("Motociclistas", "hechos_moto", "def_moto"),
    _conteo("Transporte público", "hechos_publico", "def_publico"),
    _conteo("Transporte de carga", "hechos_carga", "def_carga"),
    ("Ubicación", [
        ("municipio", "Municipio"), ("maps", "Google Maps"),
        ("coordenadas", "Coordenadas (lat, lon)"), ("lat", "Latitud"), ("lon", "Longitud"),
    ]),
]


def columnas_de(secciones) -> list[tuple[str, str]]:
    return [par for _, pares in secciones for par in pares]


NOTAS = [
    ("Fuente", "ATUS (INEGI), Zona Metropolitana de Monterrey, 2019-2024; "
               "data/processed/atus_zmm_limpio.parquet."),
    ("Cruce", "Nodo id_punto_4d (10 m de tolerancia) cuya ubicación más frecuente es "
              "«Intersección». Nombre: el par de vialidades que más se repite."),
    ("Hechos de tránsito", "Accidentes registrados en el cruce."),
    ("Defunciones", "Suma de TOTMUERTOS: conductores, pasajeros, peatones, ciclistas y otros."),
    ("Hechos con peatones", "Atropellamiento (TIPACCID = 2) o algún peatón muerto."),
    ("Hechos con ciclistas", "Colisión con ciclista (TIPACCID = 11) o algún ciclista muerto."),
    ("Hechos con peatones o ciclistas", "Unión de los dos anteriores, contada por hecho: "
                                        "un hecho con peatón y ciclista cuenta una vez."),
    ("Defunciones de peatones / ciclistas", "PEATMUERTO / CICLMUERTO (personas); la sección "
                                            "«Peatones y/o ciclistas» suma las dos."),
    ("Motociclistas", "Hechos: colisión con motocicleta (TIPACCID = 10) o alguna motocicleta "
                      "involucrada. Defunciones: todas las de esos hechos (ATUS no dice "
                      "cuántas eran motociclistas)."),
    ("Transporte público", "Hechos con camioneta de pasajeros, microbús, camión urbano u "
                           "ómnibus. Defunciones: todas las de esos hechos."),
    ("Transporte de carga", "Hechos con camión de carga o tractocamión. Defunciones: todas "
                            "las de esos hechos."),
    ("Nombres de calles", "Se comparan homologados (sin acentos, sin «Avenida»/«Calle», con "
                          "alias), así «Lázaro Cárdenas» y «Av. Lazaro Cardenas» son la misma "
                          "calle; se muestra la escritura más común."),
    ("Cruce: «A × B» o «A»", "«A × B» cuando los partes nombran dos calles distintas (el orden "
                             "no importa); si algún parte del cruce trae dos calles, gana el par más "
                             "frecuente. Solo «A» cuando ningún parte trae una segunda calle distinta: "
                             "falta, dice «NINGUNO»/«SIN REFERENCIA»/«SIN NOMBRE» o repite la calle 1."),
    ("Intersección (dos calles)", "Sí si el nombre del cruce tiene dos calles distintas; No si "
                                  "solo nombra una. Todos los puntos de la tabla están marcados "
                                  "como intersección por el agente (URBANA = 1)."),
    ("Cruces con «No»", "Un «No» con muchos hechos casi siempre es un punto por defecto, no un "
                        "cruce: el agente ubicó la calle sin el cruce y todos los partes caen "
                        "en la misma coordenada. Ej.: «Sendero Norte», 227 hechos de 2019 a "
                        "2024 en una sola coordenada (98 %). Cuéntelos con cautela."),
    ("Ranking", "El ranking va junto a los hechos de tránsito de su sección; 1 = el cruce con más. Empates comparten el lugar más alto (método «min»), "
                 "así que muchos cruces con 0 defunciones empatan en el mismo lugar."),
    ("Coordenadas", "Mediana de LATITUD y LONGITUD de los hechos del cruce (WGS84)."),
    ("Generado con", "uv run tabla-cruces (src/geostats/tabla_cruces.py)."),
]


def escribir_excel(tabla: pd.DataFrame, ruta) -> None:
    """Dos filas de encabezado: la sección (celdas combinadas) y la columna."""
    with pd.ExcelWriter(ruta, engine="openpyxl") as xl:
        tabla.to_excel(xl, sheet_name="Cruces", index=False, startrow=1)
        pd.DataFrame(NOTAS, columns=["Concepto", "Definición"]).to_excel(
            xl, sheet_name="Notas", index=False)

        hoja = xl.sheets["Cruces"]
        blanco = Font(bold=True, color="FFFFFF")
        grafito = Font(bold=True, color=GRAFITO)
        centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
        separador = Side(style="medium", color=GRAFITO)
        n = len(tabla) + 2

        col = 1
        for k, (titulo, pares) in enumerate(SECCIONES):
            ini, fin = col, col + len(pares) - 1
            # Alterna los dos tonos de la rampa ordinal para distinguir secciones.
            tono = RAMPA[k % 2]
            hoja.merge_cells(start_row=1, start_column=ini, end_row=1, end_column=fin)
            celda = hoja.cell(row=1, column=ini, value=titulo)
            celda.font, celda.alignment = blanco, centro
            for c in range(ini, fin + 1):
                hoja.cell(row=1, column=c).fill = PatternFill("solid", fgColor=tono)
                sub = hoja.cell(row=2, column=c)
                sub.font, sub.alignment = grafito, centro
                sub.fill = PatternFill("solid", fgColor=GRIS)
            # Línea gruesa a la izquierda de cada sección, de arriba abajo.
            if ini > 1:
                for fila in range(1, n + 1):
                    celda = hoja.cell(row=fila, column=ini)
                    celda.border = Border(left=separador)
            col = fin + 1

        hoja.row_dimensions[1].height = 22
        hoja.row_dimensions[2].height = 45
        hoja.freeze_panes = "B3"
        hoja.auto_filter.ref = f"A2:{get_column_letter(len(tabla.columns))}{n}"

        anchos = {"Cruce": 48, "Intersección (dos calles)": 14, "Municipio": 22, "Google Maps": 15,
                  "Coordenadas (lat, lon)": 24, "Ranking": 9}
        for k, nombre in enumerate(tabla.columns, start=1):
            letra = get_column_letter(k)
            hoja.column_dimensions[letra].width = anchos.get(nombre, 12)
            if nombre == "Ranking":
                for fila in range(3, n + 1):
                    hoja.cell(row=fila, column=k).font = Font(color=GRIS_TEXTO)
            elif nombre in ("Latitud", "Longitud"):
                for fila in range(3, n + 1):
                    hoja.cell(row=fila, column=k).number_format = "0.000000"

        col_maps = list(tabla.columns).index("Google Maps") + 1
        for fila in range(3, n + 1):
            celda = hoja.cell(row=fila, column=col_maps)
            celda.hyperlink, celda.value = celda.value, "Abrir en Maps"
            celda.style = "Hyperlink"

        notas = xl.sheets["Notas"]
        for celda in notas[1]:
            celda.font = blanco
            celda.fill = PatternFill("solid", fgColor=AZUL)
        notas.column_dimensions["A"].width = 34
        notas.column_dimensions["B"].width = 100
        for fila in notas.iter_rows(min_row=2):
            for celda in fila:
                celda.alignment = Alignment(wrap_text=True, vertical="top")


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    d = pd.read_parquet(rutas.ATUS_ZMM_LIMPIO)
    tabla = construir_tabla(d)
    escribir_excel(tabla, SALIDA)
    print(f"{len(tabla):,} cruces -> {SALIDA.relative_to(rutas.RAIZ)}")


if __name__ == "__main__":
    main()
