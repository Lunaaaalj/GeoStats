# GeoStats — Accidentes de tránsito en México (ATUS, INEGI)

Análisis geoestadístico de los accidentes de tránsito urbanos y suburbanos
registrados por el INEGI.

## Estructura

```
data/                  ← nada de esto se versiona (~5 GB)
  raw/                 descargas del INEGI, tal cual llegaron; solo lectura
    ATUS_2019..2024/   base georreferenciada anual (CSV + shapefile)
    ATUS_anual_csv/    serie anual 1997-2025, sin coordenadas
    rativ_abierto_22-26.csv
    _zips/             los comprimidos originales
  processed/           lo que genera este repo; borrable y regenerable
    atus_georreferenciado.parquet
notebooks/
  revisiones.ipynb     exploración
src/geostats/
  rutas.py             rutas del proyecto (nada de rutas relativas)
  consolidar.py        raw/ATUS_20XX → processed/*.parquet
```

La separación `raw/` vs `processed/` es la regla del proyecto: **nunca se
escribe en `raw/`**. Si algo en `processed/` se corrompe, se borra y se
regenera; si algo en `raw/` se pierde, hay que volver a bajarlo del INEGI.

## Preparar el entorno

```bash
uv sync
```

### Si `import geostats` falla

Choque conocido entre uv y Python 3.14 en macOS: el `.pth` de la instalación
editable queda con el flag `UF_HIDDEN`, y **Python 3.14 ignora en silencio los
`.pth` ocultos**. Reaparece de forma intermitente, cuando uv reescribe ese
archivo:

```bash
chflags nohidden .venv/lib/python3.14/site-packages/*.pth
```

El archivo `.env` de la raíz (`PYTHONPATH=src`) es la red de seguridad: VS Code
lo aplica al kernel de Jupyter, así que los notebooks siguen funcionando aunque
el `.pth` esté oculto. Por eso ese `.env` sí se versiona — no contiene secretos.

## Reconstruir los datos procesados

Los datos crudos no están en el repo. Bajar de INEGI las bases ATUS
georreferenciadas por año, descomprimirlas en `data/raw/ATUS_<año>/`, y correr:

```bash
uv run consolidar-atus              # parquet tabular (31 MB)
uv run consolidar-atus --geo        # además GeoParquet con geometría (43 MB)
uv run consolidar-atus --verificar  # contrasta los .shp contra los CSV
```

Produce 1,317,810 filas × 50 columnas (2019-2024) en 31 MB de Parquet, contra
219 MB de CSV.

### Por qué no se consolidan los shapefiles

Los `.shp` traen los mismos registros que los CSV. `--verificar` lo comprueba
año por año: coinciden las 1,317,810 filas por la llave `(ANIO, EDO, MPIO, ID)`,
sin sobrantes de ningún lado, y la geometría del shapefile es **idéntica** a las
columnas `LONGITUD`/`LATITUD` (desfase máximo: 0.0 grados en los seis años).

Por eso `--geo` construye la geometría desde esas columnas en vez de releer 5 GB
de shapefiles: el resultado es el mismo punto por punto. Ojo: en 2019-2023 el
orden de las filas difiere entre `.shp` y CSV, así que compararlos por posición
da resultados sin sentido — hay que unirlos por la llave.

## Notas sobre los datos

Tres cosas que no son obvias y que rompen el análisis si se ignoran:

**Encoding: CP1252 con respaldo, no lo que diga `chardet`.** Sobre estos
archivos chardet reporta `CP874`/`TIS-620` con confianza `0.00`, porque apenas
~1 de cada 250 bytes es no-ASCII. El `.cpg` del INEGI declara CP1252 y tiene
razón: en el rango `0x80-0x9F` CP1252 pone guiones y comillas tipográficas que
`latin-1` convierte en caracteres de control (719 caracteres mal leídos, en
silencio). Pero 740 bytes del origen caen en los cinco huecos que CP1252 no
define. `consolidar` registra un manejador de errores que lee esos cinco bytes
con semántica latin-1: texto correcto y cero bytes perdidos (ningún U+FFFD).

**`ID` no es llave única.** En 2019-2020 es un folio consecutivo *por
municipio* y se repite 268,920 veces; desde 2021 es un identificador compuesto.
La llave real es `(ANIO, EDO, MPIO, ID)`. `consolidar` lo valida y falla si no
se cumple.

**La cobertura crece: el panel está desbalanceado.** De 91 municipios en 2019 a
198 en 2024. El salto de +52% en accidentes entre 2020 y 2021 es en buena parte
*más municipios medidos*, no más accidentes. Cualquier serie de tiempo hay que
normalizarla (tasa por municipio, o restringir al panel balanceado).

`consolidar` agrega `CVE_MUN` (2 dígitos de estado + 3 de municipio), que es la
llave para unir con el marco geoestadístico del INEGI.
