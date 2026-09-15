# Limpieza — ATUS ZMM

Qué hace `geostats.limpieza` con `atus_zmm.parquet`, columna por columna, y qué
decidió **no** hacer.

```bash
uv run limpiar-atus          # data/processed/atus_zmm_limpio.parquet   (12.1 MB)
uv run limpiar-atus --geo    # además el GeoParquet                     (14.7 MB)
```

379,294 registros, **51 columnas de entrada → 71 de salida**. Las 51 originales
salen intactas.

---

## El principio

**La limpieza nunca borra filas y nunca imputa.** Solo agrega columnas y
banderas.

No es una preferencia de estilo. El hallazgo central de
[`calidad_datos.ipynb`](../notebooks/calidad_datos.ipynb) es que el faltante de
esta base es **MNAR**: en accidentes fatales el aliento alcohólico se ignora
2.4 veces más seguido que en los de solo daños. Con ese mecanismo, `dropna()`
sesga contra los accidentes graves e imputar bajo supuesto MAR mete sesgo en
silencio. Si la etapa de limpieza no puede borrar ni imputar, ninguna de las dos
cosas puede pasar por descuido más adelante.

Corolario práctico: el artefacto limpio es un **superconjunto** del recorte. Todo
lo que se decida tirar se tira al momento de analizar, no aquí.

## La convención de nombres

| Forma | Significa |
|---|---|
| `MAYÚSCULAS` | Tal como llegó del INEGI. Nunca se modifica, ni siquiera los códigos centinela |
| `minúsculas` | Construido por este repo |

Dos excepciones, `CVE_MUN` y `NOM_MUN`: son derivadas pero van en mayúsculas
porque siguen la nomenclatura de claves geoestadísticas del propio INEGI.

La regla existe para que en cualquier `groupby` se sepa de un vistazo si el dato
lo reportó el INEGI o lo inventamos nosotros.

---

## Las 20 columnas derivadas

Cifras medidas sobre la corrida real.

### Tiempo

| Columna | Tipo | Regla | NA |
|---|---|---|---|
| `fecha` | `datetime64` | `ANIO` + `MES` + `DIA` | 0 |
| `hora` | `Int8` | `HORA`, con `99` → NA | 0 |
| `dia_semana` | `category` ordenada | `DIASEMANA` → nombre, con `8` → NA | 0 |

Los tres salen sin un solo hueco: la ZMM **no tiene** los centinelas `DIA = 32`,
`DIASEMANA = 8` ni `HORA = 99` (a nivel nacional hay 135, 135 y 7). El código los
maneja igual, para que la misma función sirva sobre la base nacional.

**No se construye un timestamp completo**, a propósito. `MINUTOS` tiene
preferencia de dígito severa —el `0` y el `30` concentran la quinta parte de la
base—, así que una marca de tiempo al minuto afirmaría una resolución que el
dato no tiene. La hora sí es usable; el minuto no.

`fecha` cubre del **2019-01-01 al 2024-12-31** y coincide con `DIASEMANA` del
INEGI en los 379,294 registros, sin una sola discrepancia.

### Conductor presunto responsable

| Columna | Tipo | Regla | NA |
|---|---|---|---|
| `se_fugo` | `bool` | `SEXO == 1` | — (36,973 en `True`) |
| `sexo_conductor` | `category` | `2`→Hombre, `3`→Mujer; `1` → NA | 36,973 (9.75 %) |
| `edad` | `Int16` | `EDAD`, con `0` y `99` → NA | 105,659 (27.86 %) |
| `aliento_alcoholico` | `boolean` | `4`→sí, `5`→no; `6` → NA | 55,639 (14.67 %) |
| `cinturon` | `boolean` | `7`→sí, `8`→no; `9` → NA | 274,045 (72.25 %) |

El INEGI **no usa nulos**: codifica la ausencia como un valor válido del
catálogo, así que sobre las columnas originales `isna()` devuelve cero y aun así
falta hasta el 72 % de la información. Estas derivadas son las que hacen que
`isna()` diga la verdad.

Las originales se conservan porque el código distingue **«se fugó»** de **«se
ignora»**: son mecanismos distintos y colapsarlos a `NA` pierde esa
información. `se_fugo` existe justamente para sacar el primero a la superficie —
es una variable con significado propio y un predictor de gravedad, hoy escondida
dentro de dos catálogos.

> `SEXO = 1` y `EDAD = 0` marcan **exactamente los mismos 36,973 registros**:
> cuando el conductor huye no hay a quién preguntarle la edad. `validar` lo
> comprueba en cada corrida.

### Ubicación y accidente

| Columna | Tipo | Regla | NA |
|---|---|---|---|
| `ubicacion` | `category` | `URBANA` + `SUBURBANA` en 5 niveles | 0 |
| `en_interseccion` | `bool` | `URBANA == 1` | — (366,484 en `True`) |
| `n_vehiculos` | `int16` | Suma de los 13 conteos | 0 |
| `gravedad` | `category` ordenada | `CLASE` → Fatal ‹ No fatal ‹ Solo daños | 0 |
| `hay_victimas` | `bool` | `CLASE ∈ {1, 2}` | — (21,523 en `True`) |

`ubicacion` colapsa dos columnas excluyentes en una categórica legible:

| Nivel | Registros |
|---|---|
| Intersección | 366,484 |
| No intersección | 6,232 |
| Camino rural | 3,036 |
| Carretera estatal | 2,341 |
| Otro camino | 1,201 |

`gravedad` va **ordenada** para que las gráficas puedan usar la rampa ordinal de
un solo tono en vez de tres colores categóricos, que la paleta de marca no
tiene. El orden sobrevive el viaje a Parquet y de vuelta.

`n_vehiculos` va de 1 a 10, media 1.89. Nunca es cero: `validar` lo exige.

`hay_victimas` se define desde `CLASE` y se contrasta contra
`TOTMUERTOS + TOTHERIDOS > 0`. Son dos caminos que **deben** coincidir, así que
la columna de conveniencia es además una prueba de integridad.

### Vialidades

| Columna | Tipo | Regla | NA |
|---|---|---|---|
| `calle1_norm` | `string` | Recorte, espacios colapsados, mayúsculas, sin acentos | 434 (0.11 %) |
| `calle2_norm` | `string` | Igual | 5,979 (1.58 %) |
| `carretera_norm` | `string` | Igual | 373,649 (98.51 %) |
| `falta_calle2` | `bool` | `en_interseccion` y `calle2_norm` en NA | — (3,072 en `True`) |

Las originales **no se tocan**: los acentos son parte del nombre real y quitarlos
ahí sería irreversible. La normalización vive solo en la columna derivada, para
contar y para unir.

> **`Ñ` se convierte en `N`.** La descomposición NFKD separa la tilde y el
> filtro de marcas combinantes se la lleva, así que `CAÑADA DEL SUR` queda como
> `CANADA DEL SUR`. Para emparejar nombres es lo deseable, pero es una fusión
> real y por eso solo ocurre aquí.

317,416 valores cambian al normalizar. De esos, apenas **157 son espacios
sobrantes** (22 en `CALLE1`, 135 en `CALLE2`); el resto son mayúsculas y
acentos. La cadena vacía y la de puros espacios se vuelven NA: son ausencia de
información, no un nombre.

`falta_calle2` separa el hueco **real** del **estructural**. Que falte la segunda
vialidad en un accidente suburbano o fuera de intersección es esperable; que
falte en los 3,072 marcados *en* intersección no lo es, porque por definición una
intersección tiene dos vialidades. Ese es el subconjunto que vale la pena
revisar, no el total de nulos.

### Coordenadas

| Columna | Tipo | Regla | NA |
|---|---|---|---|
| `id_punto` | `string` | `"lon,lat"` exacto | 0 |
| `id_punto_4d` | `string` | `"lon,lat"` redondeado a 4 decimales (~10 m) | 0 |
| `precision_baja` | `bool` | Los **dos** ejes con ≤ 3 decimales | — (3 en `True`) |

**`id_punto` se construye con `str(float)`, no con un formato fijo.** Las
coordenadas del ATUS llegan con **hasta ocho decimales**: 235,166 longitudes y
256,918 latitudes traen siete o más. Formatearlas a seis fusiona **8,115 puntos
distintos** en silencio. `str(float)` da la representación más corta que
reconstruye el mismo float, así que el identificador es exacto sin tener que
saber de antemano cuántos decimales trae el dato — y `validar` comprueba en cada
corrida que el número de identificadores siga siendo igual al de pares de
coordenadas distintos.

Se usa una cadena legible y no un código de `factorize` para que el
identificador no cambie entre corridas y se pueda leer de vuelta.

**La tolerancia de `id_punto_4d` son 4 decimales y no 3.** A la latitud de la ZMM
(25.7 N), cuatro decimales son 11.1 m en latitud y 10.0 m en longitud: cabe
holgado dentro de un mismo cruce. Tres decimales serían 111 y 100 m, y la manzana
en Monterrey mide ~100 m, así que fusionaría cruces contiguos.

El contraste entre los dos identificadores dice algo del geocodificado:

| | Puntos distintos |
|---|---|
| Coordenada exacta | 131,180 |
| Con tolerancia de 10 m | 54,742 |

El 72.3 % de los accidentes comparte coordenada **exacta** con otro, lo que solo
se explica por reuso deliberado del nodo de la intersección. Pero esos 131,180
puntos distintos se reducen a 54,742 —el 42 %— en cuanto se les da 10 m de
tolerancia, así que muchos están a metros unos de otros. Conviven dos regímenes:
registros pegados a un catálogo de nodos y registros geocodificados
individualmente cerca de ellos.

---

## Lo que la limpieza decide no hacer

| No hace | Por qué |
|---|---|
| Imputar | El faltante es MNAR; imputar bajo MAR mete sesgo silencioso |
| Borrar filas | Solo el 25.5 % está completo en los seis campos clave; borrar deja una cuarta parte no representativa |
| Tirar columnas | El artefacto es un superconjunto; la selección se hace al analizar, con las listas de [`seleccion_datos.md`](seleccion_datos.md) |
| Meter *jitter* en las coordenadas | Es una decisión de análisis, necesita semilla y documentación. Un archivo con ruido inyectado es una mentira para cualquier otro uso |
| Canonicalizar abreviaturas de vialidad | `AV`/`AVE`/`AVENIDA` requiere un diccionario hecho a mano y valida­ción. Es un proyecto propio, con riesgo alto de fusionar calles distintas |
| Pegar la tasa de captura a cada renglón | Es un agregado: en cuanto alguien filtra la tabla, deja de significar lo que dice. Vive como función (abajo) |

---

## Verificación

`validar()` recorre **21 invariantes** y lanza excepción con la lista completa de
las que fallen. Las diez primeras son las de `calidad_datos.ipynb`, que dieron
cero violaciones sobre la base sucia: si aparecen ahora, la limpieza rompió algo.
Las demás comprueban que las derivadas dicen lo que prometen — entre ellas, que
cada columna esté en NA **exactamente** donde su original trae un centinela, ni
una fila más ni una menos, y que el número de filas no haya cambiado.

`diagnostico()` reporta, sin reprobar, las doce cifras que cambian la lectura del
análisis: `NaT` en `fecha` separando centinela de fecha imposible, discrepancias
entre `DIASEMANA` y el día real, concentración de coordenadas, y cuántos valores
de texto cambiaron al normalizar.

### `tasa_captura(datos, campo)`

Devuelve el porcentaje de registros con dato real, por municipio y año.

Existe porque el faltante de `CINTURON`, `ALIENTO` y `EDAD` mide **práctica
administrativa, no conducta vial**: va de 10.4 % en San Pedro Garza García a
100 % en Monterrey, y Guadalupe salta de 20.3 % a 96.8 % en un solo año. Ninguna
corporación cambia de criterio sobre el cinturón de un año a otro; lo que cambia
es si llenan la casilla.

Cualquier comparación entre municipios o entre años tiene que reportarse junto a
esta tabla.

---

## Correcciones a los documentos previos

Tres cosas que la corrida real dejó claras y que contradicen lo que estaba
escrito antes.

**El hallazgo 11 de `calidad_datos.ipynb` sobreestima el problema.** Dice «866
registros con ≤ 3 decimales, marcarlos y excluirlos del análisis a escala de
intersección». Ese conteo mira **solo la longitud**. Midiendo los dos ejes:

| | Registros |
|---|---|
| Longitud con ≤ 3 decimales | 866 |
| Latitud con ≤ 3 decimales | 1,028 |
| **Ambos** | **3** |
| Esperado por azar si fueran independientes | 2.3 |

El conteo conjunto es indistinguible del azar, o sea que en la ZMM **prácticamente
no hay coordenadas realmente burdas**: los 866 son floats cuya representación
resulta corta, no geocodificados gruesos. `precision_baja` exige los dos ejes por
eso, y marca 3 registros.

**`EDO` no se descarta**, aunque `seleccion_datos.md` lo ponga en la lista. Es
constante = 19 tras el recorte, pero la llave real documentada es
`(ANIO, EDO, MPIO, ID)`: sin `EDO` se rompe la verificación de duplicados y
cualquier `concat` contra la base nacional. Una columna constante en Parquet
cuesta prácticamente cero.

**`id_cruce` se llama `id_punto`.** `seleccion_datos.md` propone el primer
nombre, pero no todo punto es un cruce: 6,232 registros están marcados
explícitamente como *no* intersección y 6,578 son suburbanos.
