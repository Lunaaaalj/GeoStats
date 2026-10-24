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
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from geostats import rutas

SALIDA = rutas.RAIZ / "docs" / "cruces_zmm.xlsx"

GENERICO = re.compile(r"^(AVENIDA|AV\.?|CALLE|CALZADA|BOULEVARD|BLVD\.?|CARRETERA|"
                      r"PROLONGACI[OÓ]N|PRIVADA|ANDADOR)\s+", re.IGNORECASE)
MINUSCULAS = {"De", "Del", "La", "Las", "Los", "Y", "El"}

# Identidad GeoStats: encabezado en Azul Prusia ajustado, texto blanco.
AZUL = "005991"


def calle_limpia(calle) -> str | None:
    """Quita el genérico («Avenida», «Calle»…) y normaliza mayúsculas."""
    if not isinstance(calle, str) or not calle.strip():
        return None
    nombre = GENERICO.sub("", re.sub(r"\s+", " ", calle.strip()))
    palabras = nombre.title().split()
    return " ".join(p.lower() if p in MINUSCULAS and k else p
                    for k, p in enumerate(palabras))


def nombres_de_cruce(d: pd.DataFrame) -> pd.Series:
    """Nombre de cada nodo: el par ordenado de calles más frecuente.

    Si un nodo no tiene ningún par completo, se usa la calle 1 más frecuente.
    """
    c1 = d.CALLE1.map(calle_limpia)
    c2 = d.CALLE2.map(calle_limpia)
    completo = c1.notna() & c2.notna()
    par = pd.Series(pd.NA, index=d.index, dtype="object")
    par[completo] = [" × ".join(sorted(p)) for p in zip(c1[completo], c2[completo])]

    def moda(s: pd.Series) -> pd.Series:
        s = pd.DataFrame({"nodo": d.id_punto_4d, "v": s}).dropna()
        return s.groupby(["nodo", "v"]).size().reset_index(name="n") \
                .sort_values(["nodo", "n", "v"], ascending=[True, False, True]) \
                .drop_duplicates("nodo").set_index("nodo").v

    return moda(par).combine_first(moda(c1))


def construir_tabla(d: pd.DataFrame) -> pd.DataFrame:
    d = d.assign(
        con_peaton=d.TIPACCID.eq(2) | d.PEATMUERTO.gt(0),
        con_ciclista=d.TIPACCID.eq(11) | d.CICLMUERTO.gt(0),
        peatones_afectados=d.PEATMUERTO + d.PEATHERIDO,
        defunciones_pc=d.PEATMUERTO + d.CICLMUERTO,
    )
    g = d.groupby("id_punto_4d")
    nodos = pd.DataFrame({
        "hechos": g.size(),
        "defunciones": g.TOTMUERTOS.sum(),
        "peatones_afectados": g.peatones_afectados.sum(),
        "defunciones_pc": g.defunciones_pc.sum(),
        "hechos_peaton": g.con_peaton.sum(),
        "hechos_ciclista": g.con_ciclista.sum(),
        "def_peaton": g.PEATMUERTO.sum(),
        "def_ciclista": g.CICLMUERTO.sum(),
        "municipio": g.NOM_MUN.agg(lambda s: s.mode().iloc[0]),
        "ubicacion": g.ubicacion.agg(lambda s: s.mode().iloc[0]),
        "lat": g.LATITUD.median(),
        "lon": g.LONGITUD.median(),
    })
    cruces = nodos[nodos.ubicacion == "Intersección"].copy()
    cruces["nombre"] = nombres_de_cruce(d).reindex(cruces.index).fillna("Sin nombre")

    def lugar(col: str) -> pd.Series:
        return cruces[col].rank(ascending=False, method="min").astype(int)

    cruces["r_hechos"] = lugar("hechos")
    cruces["r_defunciones"] = lugar("defunciones")
    cruces["r_peatones"] = lugar("peatones_afectados")
    cruces["r_defunciones_pc"] = lugar("defunciones_pc")
    cruces["maps"] = [f"https://www.google.com/maps?q={la:.6f},{lo:.6f}"
                      for la, lo in zip(cruces.lat, cruces.lon)]
    cruces["coordenadas"] = [f"{la:.6f}, {lo:.6f}" for la, lo in zip(cruces.lat, cruces.lon)]

    cruces = cruces.sort_values(["hechos", "defunciones", "nombre"],
                                ascending=[False, False, True])
    return cruces.rename(columns=COLUMNAS)[list(COLUMNAS.values())]


COLUMNAS = {
    "r_hechos": "Ranking por hechos de tránsito",
    "nombre": "Cruce",
    "hechos": "Hechos de tránsito",
    "defunciones": "Defunciones",
    "r_defunciones": "Ranking por defunciones",
    "peatones_afectados": "Peatones afectados (muertos + heridos)",
    "r_peatones": "Ranking por peatones afectados",
    "defunciones_pc": "Defunciones de peatones o ciclistas",
    "r_defunciones_pc": "Ranking por defunciones de peatones o ciclistas",
    "hechos_peaton": "Hechos con peatones",
    "hechos_ciclista": "Hechos con ciclistas",
    "def_peaton": "Defunciones de peatones",
    "def_ciclista": "Defunciones de ciclistas",
    "municipio": "Municipio",
    "maps": "Google Maps",
    "coordenadas": "Coordenadas (lat, lon)",
    "lat": "Latitud",
    "lon": "Longitud",
}

NOTAS = [
    ("Fuente", "ATUS (INEGI), Zona Metropolitana de Monterrey, 2019-2024; "
               "data/processed/atus_zmm_limpio.parquet."),
    ("Cruce", "Nodo id_punto_4d (10 m de tolerancia) cuya ubicación más frecuente es "
              "«Intersección». Nombre: el par de vialidades que más se repite."),
    ("Hechos de tránsito", "Accidentes registrados en el cruce."),
    ("Defunciones", "Suma de TOTMUERTOS: conductores, pasajeros, peatones, ciclistas y otros."),
    ("Peatones afectados", "PEATMUERTO + PEATHERIDO (personas, no hechos)."),
    ("Hechos con peatones", "Atropellamiento (TIPACCID = 2) o algún peatón muerto."),
    ("Hechos con ciclistas", "Colisión con ciclista (TIPACCID = 11) o algún ciclista muerto."),
    ("Defunciones de peatones / ciclistas", "PEATMUERTO / CICLMUERTO (personas)."),
    ("Rankings", "1 = el cruce con más. Empates comparten el lugar más alto (método «min»), "
                 "así que muchos cruces con 0 defunciones empatan en el mismo lugar."),
    ("Coordenadas", "Mediana de LATITUD y LONGITUD de los hechos del cruce (WGS84)."),
    ("Generado con", "uv run tabla-cruces (src/geostats/tabla_cruces.py)."),
]


def escribir_excel(tabla: pd.DataFrame, ruta) -> None:
    with pd.ExcelWriter(ruta, engine="openpyxl") as xl:
        tabla.to_excel(xl, sheet_name="Cruces", index=False)
        pd.DataFrame(NOTAS, columns=["Concepto", "Definición"]).to_excel(
            xl, sheet_name="Notas", index=False)

        hoja = xl.sheets["Cruces"]
        encabezado = Font(bold=True, color="FFFFFF")
        relleno = PatternFill("solid", fgColor=AZUL)
        for celda in hoja[1]:
            celda.font, celda.fill = encabezado, relleno
            celda.alignment = Alignment(wrap_text=True, vertical="center")
        hoja.row_dimensions[1].height = 45
        hoja.freeze_panes = "C2"
        hoja.auto_filter.ref = hoja.dimensions

        anchos = {"Cruce": 48, "Municipio": 22, "Google Maps": 16,
                  "Coordenadas (lat, lon)": 24}
        for k, nombre in enumerate(tabla.columns, start=1):
            hoja.column_dimensions[get_column_letter(k)].width = anchos.get(nombre, 14)

        col_maps = list(tabla.columns).index("Google Maps") + 1
        for fila in range(2, len(tabla) + 2):
            celda = hoja.cell(row=fila, column=col_maps)
            celda.hyperlink, celda.value = celda.value, "Abrir en Maps"
            celda.style = "Hyperlink"

        notas = xl.sheets["Notas"]
        for celda in notas[1]:
            celda.font, celda.fill = encabezado, relleno
        notas.column_dimensions["A"].width = 34
        notas.column_dimensions["B"].width = 100


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    d = pd.read_parquet(rutas.ATUS_ZMM_LIMPIO)
    tabla = construir_tabla(d)
    escribir_excel(tabla, SALIDA)
    print(f"{len(tabla):,} cruces -> {SALIDA.relative_to(rutas.RAIZ)}")


if __name__ == "__main__":
    main()
