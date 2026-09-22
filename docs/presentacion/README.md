# Presentación — Semana de la Movilidad

`index.html` es la presentación completa en **un solo archivo de ~430 KB**: no
tiene ni una imagen. Los mapas, la curva de concentración, el calendario, la
matriz de perfiles y las series se dibujan en el navegador desde `datos.json`, y
las tipografías van embebidas, así que se abre con doble clic y se ve igual sin
conexión. **33 láminas** en cuatro partes.

## Presentar

| Tecla | Qué hace |
|---|---|
| `←` `→` `espacio` | avanzar y retroceder (también el clic y el deslizar en táctil) |
| `O` | índice navegable: salta a cualquier lámina |
| `N` | notas del presentador de la lámina actual |
| `F` | pantalla completa |
| `Esc` | cerrar los paneles |

La URL guarda la lámina (`index.html#14`). La cadena de nodos de abajo es la
barra de avance y cada nodo es un atajo. En la lámina de contenido, cada
renglón salta a su parte.

Hay cosas que responden al cursor: **pasar el ratón sobre cualquier hexágono**
dice su municipio y su cifra; en *Persistencia* los años avanzan solos y se
pueden fijar haciendo clic. Es la única lámina con fichas: *Quién pierde* y
*2027* se dividieron en una lámina por capa para que avanzar con las flechas
baste, sin tener que apuntar con el cursor.

## Cómo está armado

Debajo de las celdas van, como guía de la forma de la ciudad, las vialidades principales de OSM (`vialidades_zmm.json`, simplificadas y guardadas en el repo) y, en el mapa del país, el contorno de México (`mexico_contorno.json`, Natural Earth). El mapa hexagonal **no pertenece a ninguna lámina**: vive por encima de todas y
va cambiando de capa, de paleta y de encuadre conforme avanza la narración. Es
el hilo que une las cuatro partes. Cada lámina lo configura con atributos:

```html
<section class="slide" data-capa="p2027" data-rampa="calida"
         data-marco="derecha" data-velo="claro">
```

| Atributo | Valores |
|---|---|
| `data-capa` | `total`, `a2019`…`a2024`, `moto`, `peaton`, `ciclista`, `victimas`, `heridos`, `muertos` (defunciones), `anillos`, `p2027`, `ptop5`, `ninguna` |
| `data-mapa` | `mx` cambia al mapa del país; al salir de esa lámina se acerca hasta Monterrey y entrega el relevo al de la ZMM |
| `data-corredores` | `si` apaga la rejilla y dibuja las seis avenidas con sus propios cruces |
| `data-rampa` | `fria` (lo observado) · `calida` (lo estimado) |
| `data-marco` | `llena`, `derecha`, `zoom`, `corredor`, `mini`, `fuera` |
| `data-velo` | `claro` (degradado), `lleno` (sólido), `tinta` (sobre azul) |
| `data-cruces` | `si` para superponer los 600 cruces con más accidentes |
| `data-etiquetas` | `si` numera los diez peores cruces sobre el mapa y atenúa el resto |
| `data-notas` | el texto que muestra la tecla `N` |
| `data-paso` | (en un elemento con `data-anim`) se revela de uno en uno con la tecla de avanzar; la lámina cambia hasta que no queda nada por decir |

Sobre fondo azul la rampa se invierte (`friaNoche`, `calidaNoche`): con la
rampa clara el mapa desaparecería dentro del fondo.

## Regenerar

Se editan `plantilla.html` y `datos.py`; `index.html` **se genera**:

```bash
uv run python docs/presentacion/datos.py                      # datos.json, ~2 min
uv run --with segno --no-project python docs/presentacion/construir.py
```

`datos.py` lee `processed/` y deja en `datos.json` las 13 capas de las 2 241
celdas, la retícula nacional de 0,1°, las 168 horas, la curva de concentración,
las series municipales, los cruces, las vialidades, los seis corredores y los
centroides del agrupamiento de cruces. `construir.py` sustituye las marcas de la plantilla:

| Marca | Qué inserta |
|---|---|
| `{{DATOS}}` | `datos.json` completo |
| `{{FUENTE:montserrat}}` | `fuentes/montserrat.woff2` en base64 |
| `{{QR_LADO:<url>}}` · `{{QR_TRAZO:<url>}}` | el QR de esa liga como trazado SVG |

Para el PDF:

```bash
chrome --headless --no-pdf-header-footer --force-prefers-reduced-motion \
  --print-to-pdf=docs/presentacion.pdf docs/presentacion/index.html
```

`--force-prefers-reduced-motion` es necesario: sin él las láminas se imprimen a
medio aparecer. Al imprimir, cada lámina recibe su propia copia del mapa —el
original es uno solo y no puede estar en 32 páginas a la vez.

## Diseño

Sigue el manual de identidad de GeoStats: la paleta de seis colores, las tres
tipografías (Montserrat, Cormorant Garamond, Roboto Mono) y su vocabulario
gráfico. La red de nodos del manual no se dibuja como adorno: **es el propio
mapa**, porque los 54 742 cruces de la metrópoli son literalmente una red de
nodos.

Las marcas de datos usan `#005991` y no el `#003153` de marca: la validación de
color del README raíz lo descarta como serie sobre fondo claro. El azul de
marca se reserva para superficies y texto.

## Qué quedó fuera a propósito

La Parte 3 presenta **solo los resultados del modelo**: no hay láminas de
método ni de validación. Lo que se retiró —qué se puede predecir y qué no, por
qué hexágonos, cómo está armado el modelo y cuánto acierta en 2024— vive en las
**notas del presentador** (tecla `N`) de las láminas vecinas, para poder
mencionarlo o contestarlo sin proyectarlo.

## Una advertencia sobre el mapa del país

La lámina 4 muestra el país entero, pero lo que dibuja es **dónde reporta
ATUS**, no dónde hay accidentes: el noroeste sale casi vacío porque esos
municipios no reportan, no porque no choquen. Está rotulado así a propósito y
sirve para justificar el recorte a la ZMM. Para dibujar la silueta real de
México haría falta un shapefile del país, que no está en el repositorio.
