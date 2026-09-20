"""Mapa de calor de los accidentes acumulados 2019-2024 en la ZMM, sobre calles.

Uso: PYTHONPATH=src .venv/bin/python notebooks/mapa_calor.py [salida.png]
Necesita red: el mapa base son teselas de Esri (World Light Gray).
"""
import sys
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib import patheffects
from scipy.ndimage import gaussian_filter
import contextily as cx
import xyzservices

from geostats import rutas, espacial

AZUL, ROJO, GRAFITO, GRIS, BLANCO = "#005991", "#8B2C1A", "#2C2C2C", "#F2F2F2", "#FFFFFF"
TITULAR = ["Montserrat", "Helvetica Neue", "Arial", "DejaVu Sans"]
TEXTO = ["Cormorant Garamond", "EB Garamond", "Georgia", "DejaVu Serif"]
CIFRAS = ["Roboto Mono", "Menlo", "DejaVu Sans Mono"]
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": TITULAR,
                     "font.serif": TEXTO, "font.monospace": CIFRAS})

SALIDA = sys.argv[1] if len(sys.argv) > 1 else rutas.RAIZ / "docs" / "mapa_calor_zmm.png"
CELDA = 50           # m, resolución del histograma
SUAVIZADO = 200      # m, desviación del kernel gaussiano
ZOOM = 13

# Recorte: percentiles 1-99 de los puntos, ensanchado a la proporción del panel del mapa.
FIG = (16, 9); ANCHO_MAPA = 0.68
Y0, Y1 = 2_821_000, 2_868_000
alto_km = Y1 - Y0
ancho_km = alto_km * (FIG[0] * ANCHO_MAPA) / FIG[1]
xc = 366_500
X0, X1 = xc - ancho_km / 2, xc + ancho_km / 2

ESRI_BASE = cx.providers.Esri.WorldGrayCanvas
ESRI_ETIQUETAS = xyzservices.TileProvider(
    name="Esri.WorldGrayReference", attribution="Esri",
    url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
)

g = gpd.read_parquet(rutas.ATUS_ZMM_LIMPIO_GEO).to_crs(espacial.UTM_ZMM)
x, y = g.geometry.x.values, g.geometry.y.values
dentro = (x >= X0) & (x <= X1) & (y >= Y0) & (y <= Y1)
print(f"{len(g):,} accidentes; {dentro.mean():.1%} dentro del recorte de {ancho_km/1000:.0f} × {alto_km/1000:.0f} km")

# Densidad: accidentes por km², suavizada.
xe = np.arange(X0, X1 + CELDA, CELDA); ye = np.arange(Y0, Y1 + CELDA, CELDA)
h, xe, ye = np.histogram2d(x[dentro], y[dentro], bins=[xe, ye])
dens = gaussian_filter(h.T, sigma=SUAVIZADO / CELDA) / (CELDA / 1000) ** 2
tope = np.percentile(dens[dens > 0], 99.8)
print(f"densidad máxima {dens.max():,.0f} acc/km²; tope de la rampa {tope:,.0f}")

# Clases discretas de un solo tono: cada mancha es de color uniforme, sin
# degradado interno. Los umbrales son fracciones del tope (que es el percentil
# 99.8); por debajo del primero no se pinta nada y las calles quedan a la vista.
UMBRALES = np.array([0.04, 0.12, 0.28, 0.55, 1.0]) * tope
rampa = ListedColormap([
    (0.63, 0.79, 0.91, 0.55),   # #a0c9e8
    (0.41, 0.67, 0.88, 0.80),   # #68abe0
    (0.11, 0.47, 0.72, 0.90),   # #1b77b8
    (0.00, 0.35, 0.57, 0.97),   # #005991
], name="geostats_calor_clases")
rampa.set_under((1, 1, 1, 0)); rampa.set_over((0.00, 0.35, 0.57, 0.97))
norma = BoundaryNorm(UMBRALES, ncolors=rampa.N)

fig = plt.figure(figsize=FIG, facecolor=BLANCO)
ax = fig.add_axes([0, 0, ANCHO_MAPA, 1])
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal"); ax.set_axis_off()

cx.add_basemap(ax, crs=espacial.UTM_ZMM, source=ESRI_BASE, zoom=ZOOM, attribution=False, zorder=1)
im = ax.imshow(dens, extent=[xe[0], xe[-1], ye[0], ye[-1]], origin="lower", cmap=rampa,
               norm=norma, interpolation="nearest", zorder=2)
cx.add_basemap(ax, crs=espacial.UTM_ZMM, source=ESRI_ETIQUETAS, zoom=ZOOM, attribution=False, zorder=3, alpha=0.9)

# Escala.
bx, by = X0 + 0.03 * (X1 - X0), Y0 + 0.04 * (Y1 - Y0)
halo = [patheffects.withStroke(linewidth=5, foreground=BLANCO)]
ax.plot([bx, bx + 5000], [by, by], color=GRAFITO, lw=3, solid_capstyle="butt", zorder=5, path_effects=halo)
ax.text(bx, by + 0.01 * (Y1 - Y0), "5 km", fontsize=10, color=GRAFITO, fontfamily="monospace", zorder=5, path_effects=halo)

# Panel lateral: título, lectura, leyenda, fuente.
px = ANCHO_MAPA + 0.035
fig.text(px, 0.90, "Dónde\nchocamos", fontsize=40, fontweight="bold", color=ROJO, va="top", ha="left", linespacing=1.05)
fig.text(px, 0.705, f"{dentro.sum():,}", fontsize=34, color=AZUL, va="top", ha="left", fontfamily="monospace")
fig.text(px, 0.645, "accidentes de tránsito georreferenciados\nen la Zona Metropolitana de Monterrey,\n2019 a 2024, acumulados.",
         fontsize=13, color=GRAFITO, va="top", ha="left", linespacing=1.55)
# Concentración: qué fracción del área con accidentes reúne la mitad de ellos (celdas de 100 m, sin suavizar).
h100, _, _ = np.histogram2d(x, y, bins=[np.arange(x.min(), x.max() + 100, 100), np.arange(y.min(), y.max() + 100, 100)])
v = np.sort(h100[h100 > 0])[::-1]
k50 = np.searchsorted(np.cumsum(v) / v.sum(), 0.5) + 1
print(f"la mitad de los accidentes cae en {k50:,} celdas de 100 m ({k50 / len(v):.1%} del área con accidentes, {k50 / 100:.0f} km²)")
fig.text(px, 0.50, "La mitad de los accidentes", fontsize=13, color=GRAFITO, va="top", ha="left")
fig.text(px, 0.465, f"cabe en {k50 / 100:.0f} km²", fontsize=26, color=AZUL, va="top", ha="left", fontweight="bold")
fig.text(px, 0.395, f"el {k50 / len(v):.0%} del área donde ocurre alguno.\nSon las grandes avenidas y sus cruces:\n"
         "el color es la densidad por km², suavizada\ncon un kernel de 200 m.",
         fontsize=11.5, color=GRAFITO, va="top", ha="left", linespacing=1.55)

cax = fig.add_axes([px, 0.165, 0.25, 0.022])
cb = fig.colorbar(im, cax=cax, orientation="horizontal", extend="max", spacing="uniform")
cb.set_ticks(UMBRALES)
cb.set_ticklabels([f"{u:,.0f}" for u in UMBRALES[:-1]] + [f"{UMBRALES[-1]:,.0f}+"])
cb.ax.tick_params(labelsize=10, colors=GRAFITO, length=0)
for t in cb.ax.get_xticklabels(): t.set_fontfamily("monospace")
cb.outline.set_visible(False)
fig.text(px, 0.21, "accidentes por km²", fontsize=11, color=GRAFITO, va="bottom", ha="left")

fig.text(px, 0.06, "Fuente: INEGI, Accidentes de Tránsito Terrestre en Zonas\nUrbanas y Suburbanas (ATUS), 2019-2024.\n"
         "Mapa base: Esri World Light Gray.", fontsize=9, color="#6B6B6B", va="bottom", ha="left", linespacing=1.5)
fig.text(0.985, 0.06, "GeoStats", fontsize=11, color=ROJO, fontweight="bold", va="bottom", ha="right")

fig.savefig(SALIDA, dpi=200, facecolor=BLANCO)
print("→", SALIDA)
