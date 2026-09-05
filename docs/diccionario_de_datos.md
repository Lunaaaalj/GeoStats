# Diccionario de datos — ATUS georreferenciado

Accidentes de tránsito terrestre en zonas urbanas y suburbanas (ATUS), INEGI.
Base georreferenciada **2019–2024**: 1,317,810 registros, 50 columnas.

Este documento consolida las tres fuentes de metadatos que vienen en `data/raw/`,
y añade una columna con lo que **realmente aparece** en los datos:

| Fuente | Qué aporta |
|---|---|
| `ATUS_<año>/diccionario_de_datos/fd_bd_atus_georreferenciacion.xlsx` | Códigos y rangos de los 50 campos. Los seis años son idénticos salvo el rango de `ANIO` y la descripción de `OID`. |
| `ATUS_anual_csv/diccionario_de_datos/diccionario_de_datos_atus_anual_1997_2025.csv` | Definiciones extensas de los mismos campos (qué cuenta como cada tipo de vehículo, cómo se define cada tipo de accidente). |
| `ATUS_anual_csv/catalogos/tc_*.csv` | Catálogos de entidad, municipio, día, hora, minuto, mes y edad. |

> **Los rangos del diccionario no siempre coinciden con los datos.** La columna
> «Observado» se calcula sobre el parquet consolidado; las diferencias están
> listadas en [Discrepancias](#discrepancias-entre-el-diccionario-y-los-datos).

---

## Índice

- [Identificación y ubicación](#identificación-y-ubicación)
- [Tiempo](#tiempo)
- [Tipo de zona y de accidente](#tipo-de-zona-y-de-accidente)
- [Vehículos involucrados](#vehículos-involucrados)
- [Conductor presunto responsable](#conductor-presunto-responsable)
- [Víctimas](#víctimas)
- [Vialidad y coordenadas](#vialidad-y-coordenadas)
- [Códigos centinela](#códigos-centinela)
- [Discrepancias entre el diccionario y los datos](#discrepancias-entre-el-diccionario-y-los-datos)
- [Catálogo de entidades](#catálogo-de-entidades)
- [Campos de la serie anual ausentes aquí](#campos-de-la-serie-anual-ausentes-aquí)

---

## Identificación y ubicación

| Campo | Tipo | Descripción | Rango documentado | Observado |
|---|---|---|---|---|
| `ID` | Numérico (5) | Número de identificación del registro | `001 – N` | 1,048,890 valores distintos, **no único** (268,920 repetidos) |
| `EDO` | Numérico (2) | Clave de la entidad federativa | `01 – 32` | 1–32, las 32 entidades |
| `MPIO` | Numérico (3) | Clave del municipio dentro de la entidad | `001 – N` | 1–385 |
| `CVE_MUN` | Texto (5) | *Derivado por este repo*: `EDO` + `MPIO` con ceros a la izquierda | — | 198 municipios distintos |
| `OID` | Numérico (5) | Identificador generado por QGIS al georreferenciar | `001 – N` | *Descartado al consolidar*: solo existe en 2022–2024 |

`ID` **no identifica un accidente por sí solo.** En 2019–2020 es un folio
consecutivo por municipio (`"8"`, `"234"`); desde 2021 es un identificador
compuesto (`"1170966-999-0"`). La llave real es `(ANIO, EDO, MPIO, ID)`, que sí
es única en los 1,317,810 registros.

`CVE_MUN` no viene en el origen: lo agrega `geostats.consolidar` porque es la
clave de 5 dígitos con la que se une al marco geoestadístico del INEGI.

---

## Tiempo

| Campo | Tipo | Descripción | Rango documentado | Observado |
|---|---|---|---|---|
| `ANIO` | Numérico (4) | Año en que ocurrió el accidente | `2019 – 2024` | 2019–2024 |
| `MES` | Numérico (2) | Mes | `1 – 12` | 1–12 |
| `DIA` | Numérico (2) | Día del mes | `1 – 31` | 1–32 (incluye el centinela 32) |
| `DIASEMANA` | Numérico (1) | Día de la semana | `1 – 7` | 1–8 (incluye el centinela 8) |
| `HORA` | Numérico (2) | Hora, sin minutos | `0 – 23` | 0–99 (incluye el centinela 99) |
| `MINUTOS` | Numérico (2) | Minutos | `0 – 59` | 0–99 (incluye el centinela 99) |

**`DIASEMANA`**

| Código | Día | Registros |
|---|---|---|
| `1` | Lunes | 186,322 |
| `2` | Martes | 182,666 |
| `3` | Miércoles | 182,904 |
| `4` | Jueves | 184,925 |
| `5` | Viernes | 205,946 |
| `6` | Sábado | 204,405 |
| `7` | Domingo | 170,507 |
| `8` | No especificado | 135 |

**`MES`** se corresponde con `tc_periodo_mes.csv` (1 = Enero … 12 = Diciembre).

> Los minutos muestran fuerte preferencia de dígito: el valor `0` aparece
> 157,425 veces y el `30` 119,320,
> contra ~10,000 de un minuto cualquiera. La hora del accidente está redondeada
> en buena parte de los registros.

---

## Tipo de zona y de accidente

`URBANA` y `SUBURBANA` son excluyentes: un accidente está en una zona o en la
otra, y el campo de la zona que no aplica lleva `0`. Se verificó que no hay
registros con ambos en `0` ni con ambos distintos de `0`.

**`URBANA`** — 1,287,933 registros (97.73%)

| Código | Significado | Registros |
|---|---|---|
| `0` | El accidente corresponde a la zona suburbana | 29,877 |
| `1` | Accidente en intersección | 1,157,890 |
| `2` | Accidente en no intersección | 130,043 |

**`SUBURBANA`** — 29,877 registros (2.27%)

| Código | Significado | Registros |
|---|---|---|
| `0` | El accidente corresponde a la zona urbana | 1,287,933 |
| `1` | Accidente en camino rural | 5,498 |
| `2` | Accidente en carretera estatal | 20,705 |
| `3` | Accidente en otro camino | 3,674 |

**`TIPACCID`** — tipo de accidente

| Código | Tipo | Definición (diccionario de la serie anual) | Registros |
|---|---|---|---|
| `1` | Colisión con vehículo automotor | Encuentro violento de dos o más vehículos en una vía de circulación. Puede ser lateral, frontal o por alcance. | 873,201 |
| `2` | Colisión con peatón (atropellamiento) | Un vehículo de motor arrolla o golpea a una persona que transita en la vía pública. | 39,636 |
| `3` | Colisión con animal | Un vehículo de motor arrolla a cualquier tipo de animal. | 965 |
| `4` | Colisión con objeto fijo | Encuentro con un objeto sujeto o asentado en el piso: postes, guarniciones, árboles. Incluye chocar contra un vehículo estacionado. | 172,093 |
| `5` | Volcadura | El vehículo pierde su posición normal, incluso da una o varias volteretas. | 20,438 |
| `6` | Caída de pasajero | Una o más personas que viajan en el vehículo, excluyendo al conductor, caen fuera de él. | 5,218 |
| `7` | Salida del camino | El vehículo abandona de manera violenta e imprevista la vía por la que transita. | 15,558 |
| `8` | Incendio | Fuego por corto circuito o derrame de combustible. No aplica si resulta de una colisión previa. | 852 |
| `9` | Colisión con ferrocarril | Choque con locomotora, vagón u otro vehículo de transporte ferroviario. | 776 |
| `10` | Colisión con motocicleta | Encuentro violento entre un vehículo automotor y una motocicleta, o entre dos motocicletas. | 160,646 |
| `11` | Colisión con ciclista | Un vehículo automotor arrolla a un ciclista. | 13,683 |
| `12` | Otro | Derrumbes, deslaves u otro objeto que caiga sobre vehículos en circulación. | 14,744 |

**`CAUSAACCI`** — causa probable o presunta

| Código | Causa | Registros |
|---|---|---|
| `1` | Conductor | 1,255,813 |
| `2` | Peatón o pasajero | 7,854 |
| `3` | Falla del vehículo | 8,596 |
| `4` | Mala condición del camino | 27,116 |
| `5` | Otra | 18,431 |

**`CAPAROD`** — capa de rodamiento

| Código | Superficie | Registros |
|---|---|---|
| `1` | Pavimentada — concreto hidráulico o carpeta asfáltica | 1,307,997 |
| `2` | No pavimentada — materiales naturales (piedra, tezontle) | 9,813 |

**`CLASE`** — clase del accidente

| Código | Clase | Definición | Registros |
|---|---|---|---|
| `1` | Fatal | Una o más personas fallecen en el lugar del evento. | 9,493 |
| `2` | No fatal | Una o más personas resultan lesionadas. | 189,179 |
| `3` | Sólo daños | Únicamente daños materiales. | 1,119,138 |

---

## Vehículos involucrados

Trece conteos, uno por tipo de vehículo. Cada uno indica **cuántos vehículos de
ese tipo participaron** en el accidente, no si participó alguno. La clasificación
del INEGI se basa en el número de asientos o la capacidad de carga:

| Campo | Tipo de vehículo | Criterio de clasificación | Máx. observado | Accidentes con ≥1 |
|---|---|---|---|---|
| `AUTOMOVIL` | Automóvil | Hasta 7 asientos, incluido el del conductor | 9 | 1,101,641 |
| `CAMPASAJ` | Camioneta de pasajeros | De 8 a 15 asientos | 5 | 261,785 |
| `MICROBUS` | Microbús | De 16 a 20 asientos | 3 | 6,797 |
| `PASCAMION` | Camión urbano de pasajeros | De 21 a 29 asientos, con rutas fijas | 5 | 62,839 |
| `OMNIBUS` | Ómnibus | 30 o más asientos, con horarios y destinos establecidos | 5 | 6,877 |
| `TRANVIA` | Tren eléctrico o trolebús | Propulsión eléctrica por cable aéreo, sin rieles | 1 | 331 |
| `CAMIONETA` | Camioneta de carga | Capacidad de hasta 999 kg | 7 | 151,779 |
| `CAMION` | Camión de carga | Capacidad de 1,000 a 5,000 kg | 8 | 55,025 |
| `TRACTOR` | Tractor con o sin remolque | Diseñado para remolcar; excluye tractores agrícolas | 9 | 37,894 |
| `FERROCARRI` | Ferrocarril | Transporte sobre rieles | 2 | 1,130 |
| `MOTOCICLET` | Motocicleta | Dos, tres o cuatro ruedas, hasta 400 kg | 8 | 195,363 |
| `BICICLETA` | Bicicleta | Propulsada por esfuerzo humano | 4 | 15,490 |
| `OTROVEHIC` | Otro | Ambulancias, grúas, tracción animal, tractores agrícolas | 8 | 18,983 |

Todos los registros tienen al menos un vehículo involucrado: la suma de los trece
campos es mayor que cero en los 1,317,810 registros.

---

## Conductor presunto responsable

Cuatro campos describen al conductor señalado como responsable. **Los cuatro
tienen tasas altas de información ausente, codificada como valor válido.**

**`SEXO`**

| Código | Significado | Registros | % |
|---|---|---|---|
| `1` | Se fugó — sexo desconocido | 124,249 | 9.43% |
| `2` | Hombre | 965,713 | 73.28% |
| `3` | Mujer | 227,848 | 17.29% |

El código `1` no es una categoría de sexo: marca que el conductor huyó del lugar.

**`ALIENTO`** — aliento alcohólico

| Código | Significado | Registros | % |
|---|---|---|---|
| `4` | Sí | 46,833 | 3.55% |
| `5` | No | 947,286 | 71.88% |
| `6` | Se ignora | 323,691 | 24.56% |

**`CINTURON`** — uso de cinturón de seguridad

| Código | Significado | Registros | % |
|---|---|---|---|
| `7` | Sí | 199,207 | 15.12% |
| `8` | No | 134,755 | 10.23% |
| `9` | Se ignora | 983,848 | 74.66% |

**`EDAD`** — edad del conductor presunto responsable

| Código | Significado | Registros | % |
|---|---|---|---|
| `12`–`98` | Edad en años | 1,015,118 | 77.03% |
| `0` | Se ignora porque se fugó | 124,249 | 9.43% |
| `99` | No especificado | 178,443 | 13.54% |

Edades válidas: mínimo 12, máximo 98, media 37.8 años.
No hay valores fuera del rango `12`–`98` además de los dos centinelas.

`EDAD = 0` y `SEXO = 1` marcan **exactamente los mismos registros**: cuando el
conductor se fuga no hay a quién preguntarle la edad. Verificado sobre los
1,317,810 registros.

---

## Víctimas

Diez conteos por tipo de víctima, más dos totales. Todos en rango `0–99`.

| Campo | Descripción | Máx. observado | Suma 2019–2024 |
|---|---|---|---|
| `CONDMUERTO` | Conductores muertos en el lugar | 4 | 4,800 |
| `CONDHERIDO` | Conductores heridos | 7 | 124,310 |
| `PASAMUERTO` | Pasajeros muertos (excluye al conductor) | 12 | 1,847 |
| `PASAHERIDO` | Pasajeros heridos | 41 | 80,054 |
| `PEATMUERTO` | Peatones muertos | 4 | 3,095 |
| `PEATHERIDO` | Peatones heridos | 8 | 41,368 |
| `CICLMUERTO` | Ciclistas muertos | 2 | 418 |
| `CICLHERIDO` | Ciclistas heridos | 14 | 7,390 |
| `OTROMUERTO` | Otras personas muertas (p. ej. dentro de inmuebles o trabajando en la vía) | 1 | 62 |
| `OTROHERIDO` | Otras personas heridas | 3 | 574 |
| `TOTMUERTOS` | **Total de muertos** | 12 | 10,222 |
| `TOTHERIDOS` | **Total de heridos** | 42 | 253,696 |

Los totales cuadran: `TOTMUERTOS` es exactamente la suma de los cinco campos de
muertos y `TOTHERIDOS` la de los cinco de heridos, sin una sola excepción.
`CLASE` también es coherente con ellos (ningún accidente «Fatal» con cero
muertos, ningún «Sólo daños» con víctimas).

---

## Vialidad y coordenadas

| Campo | Tipo | Descripción | Nulos | Valores únicos |
|---|---|---|---|---|
| `CALLE1` | Texto (570) | Vialidad principal donde se registró el accidente | 3,661 (0.28%) | 82,694 |
| `CALLE2` | Texto (570) | Vialidad secundaria (la que cruza, en intersecciones) | 44,805 (3.40%) | 104,312 |
| `CARRETERA` | Texto (570) | Nombre de la carretera, en accidentes suburbanos | 1,274,293 (96.70%) | 10,810 |

| Campo | Tipo | Descripción | Rango observado |
|---|---|---|---|
| `LONGITUD` | Decimal | Longitud geográfica del accidente | -117.123081 a -86.742763 |
| `LATITUD` | Decimal | Latitud geográfica del accidente | 14.708967 a 32.671710 |

Sistema de referencia: **WGS 84 (`EPSG:4326`)**, según el `.prj` de los seis años.
No hay coordenadas nulas ni fuera del territorio nacional.

`CARRETERA` está vacío en el 96.70% de los registros
porque solo aplica a accidentes suburbanos. `CALLE2` está vacío cuando no hay
intersección — pero también en 20,389
accidentes marcados *en* intersección, donde por definición debería haber dos
vialidades.


---

## Códigos centinela

El INEGI **no usa valores nulos** en los campos numéricos: la ausencia de
información se codifica como un valor válido del catálogo. Un `df.isna()` no
detecta nada de esto.

| Campo | Código | Significado | Registros | % del total |
|---|---|---|---|---|
| `CINTURON` | `9` | Se ignora | 983,848 | 74.66% |
| `ALIENTO` | `6` | Se ignora | 323,691 | 24.56% |
| `EDAD` | `99` | No especificado | 178,443 | 13.54% |
| `SEXO` | `1` | Se fugó — sexo desconocido | 124,249 | 9.43% |
| `EDAD` | `0` | Se ignora porque se fugó | 124,249 | 9.43% |
| `DIA` | `32` | No especificado | 135 | 0.01% |
| `DIASEMANA` | `8` | No especificado | 135 | 0.01% |
| `HORA` | `99` | No especificado | 7 | 0.00% |
| `MINUTOS` | `99` | No especificado | 7 | 0.00% |

Solo **309,863 registros (23.51 %)** tienen información en los seis campos
de arriba.

Los catálogos `tc_edad.csv`, `tc_dia.csv`, `tc_hora.csv` y `tc_minuto.csv`
documentan estos centinelas explícitamente; el diccionario de la base
georreferenciada los menciona solo en la columna de observaciones.

Existe además el código **`0` «Certificado cero»** —el municipio reportó no haber
tenido accidentes—, documentado para `DIA`, `DIASEMANA`, `TIPACCID`, `CAUSAACCI`,
`CAPAROD`, `SEXO`, `ALIENTO`, `CINTURON` y `CLASE`. **No aparece en ningún
registro de la base georreferenciada**, lo cual es consistente: un certificado
cero no tiene coordenadas que georreferenciar.

---

## Discrepancias entre el diccionario y los datos

Diferencias verificadas sobre los 1,317,810 registros. En todos los casos **los datos
son correctos y el diccionario está incompleto o equivocado**.

| Campo | Dice el diccionario | Está en los datos | Lectura |
|---|---|---|---|
| `LONGITUD` | «Valor en formato decimal siempre positivo» | -117.1231 a -86.7428, siempre negativo | Observación invertida: México está al **oeste** del meridiano de Greenwich |
| `LATITUD` | «Valor en formato decimal siempre negativo» | 14.7090 a 32.6717, siempre positiva | Observación invertida: México está en el hemisferio **norte** |
| `URBANA` | Rango `1 – 2` | 0–2 | El `0` sí es válido y está documentado en las observaciones del mismo diccionario |
| `SUBURBANA` | Rango `1 – 3` | 0–3 | Igual que el anterior |
| `DIA` | Rango `1 – 31` | 1–32 | La columna de rango omite el centinela `32` |
| `DIASEMANA` | Rango `1 – 7` | 1–8 | Omite el centinela `8` |
| `HORA` | Rango `0 – 23` | 0–99 | Omite el centinela `99` |
| `MINUTOS` | Rango `0 – 59` | 0–99 | Omite el centinela `99` |
| `EDAD` | Rango `12 – 98` | 0–99 | Omite los centinelas `0` y `99` |
| `CLASE` | Rango `0 – 9` | 1–3 | El `0-9` es el ancho del campo, no el dominio: solo hay tres clases |
| Vehículos | Rango `1 – 9` | mínimo 0 | El diccionario de la serie anual dice `0 – 9`, que sí concuerda. Los dos diccionarios del INEGI se contradicen |
| `ID` | «001 – N», identificador del registro | 268,920 valores repetidos | No es llave. La llave es `(ANIO, EDO, MPIO, ID)` |

---

## Catálogo de entidades

De `tc_entidad.csv`, con los registros observados en la base georreferenciada.
La cobertura **no es nacional**: solo incluye municipios con zonas urbanas
seleccionadas, y crece de 91 municipios en 2019 a 198 en 2024.

| Clave | Entidad | Municipios en la base | Registros |
|---|---|---|---|
| `01` | Aguascalientes | 6 | 21,763 |
| `02` | Baja California | 4 | 48,936 |
| `03` | Baja California Sur | 4 | 21,275 |
| `04` | Campeche | 2 | 14,412 |
| `05` | Coahuila de Zaragoza | 8 | 36,886 |
| `06` | Colima | 4 | 21,707 |
| `07` | Chiapas | 5 | 7,979 |
| `08` | Chihuahua | 4 | 84,268 |
| `09` | Ciudad de México | 16 | 38,185 |
| `10` | Durango | 3 | 41,133 |
| `11` | Guanajuato | 7 | 47,452 |
| `12` | Guerrero | 2 | 16,266 |
| `13` | Hidalgo | 3 | 7,806 |
| `14` | Jalisco | 9 | 58,020 |
| `15` | México | 26 | 45,194 |
| `16` | Michoacán de Ocampo | 6 | 41,556 |
| `17` | Morelos | 12 | 22,067 |
| `18` | Nayarit | 3 | 4,763 |
| `19` | Nuevo León | 18 | 379,294 |
| `20` | Oaxaca | 3 | 8,480 |
| `21` | Puebla | 6 | 39,315 |
| `22` | Querétaro | 5 | 39,234 |
| `23` | Quintana Roo | 4 | 24,787 |
| `24` | San Luis Potosí | 3 | 27,269 |
| `25` | Sinaloa | 4 | 24,982 |
| `26` | Sonora | 6 | 94,496 |
| `27` | Tabasco | 1 | 2,162 |
| `28` | Tamaulipas | 9 | 54,015 |
| `29` | Tlaxcala | 2 | 3,974 |
| `30` | Veracruz de Ignacio de la Llave | 8 | 22,160 |
| `31` | Yucatán | 3 | 13,560 |
| `32` | Zacatecas | 2 | 4,414 |

El catálogo completo de municipios está en
`data/raw/ATUS_anual_csv/catalogos/tc_municipio.csv` (2,511
municipios del país), con la clave `CVEGEO` de 5 dígitos que corresponde a la
columna derivada `CVE_MUN`.

---

## Campos de la serie anual ausentes aquí

La serie anual `ATUS_anual_csv` (1997–2025) cubre más años y más
municipios, pero **no trae coordenadas**. Estos campos suyos no existen en la
base georreferenciada:

| Campo | Descripción |
|---|---|
| `COBERTURA` | Área geográfica a la que están referidos los indicadores |
| `CVEGEO` | Clave geoestadística de 5 dígitos (equivale al `CVE_MUN` derivado aquí) |
| `NEMUERTO` | Víctimas muertas que la fuente informante no clasificó |
| `NEHERIDO` | Víctimas heridas que la fuente informante no clasificó |
| `ESTATUS` | Estatus de las cifras: definitivas, preliminares, revisadas o corregidas |

`CLASACC` en la serie anual equivale a `CLASE` aquí; `ID_EDAD`, `ID_HORA`,
`ID_MINUTO`, `ID_DIA`, `ID_ENTIDAD` e `ID_MUNICIPIO` equivalen a `EDAD`, `HORA`,
`MINUTOS`, `DIA`, `EDO` y `MPIO`. La diferencia de fondo: la serie anual guarda
**etiquetas de texto** («Colisión con peatón») donde la georreferenciada guarda
**códigos numéricos**.

La ausencia de `NEMUERTO`/`NEHERIDO` explica por qué aquí los totales cuadran
exactamente con la suma de sus componentes.

---

## Fuentes

- INEGI, *Accidentes de tránsito terrestre en zonas urbanas y suburbanas (ATUS)*.
- Diccionarios en `data/raw/ATUS_<año>/diccionario_de_datos/` y
  `data/raw/ATUS_anual_csv/diccionario_de_datos/`.
- Catálogos en `data/raw/ATUS_anual_csv/catalogos/`.
- Metadatos en `data/raw/ATUS_<año>/metadatos/`.

Las columnas «Observado» y todos los conteos se calculan sobre
`data/processed/atus_georreferenciado.parquet`. Para regenerarlo:
`uv run consolidar-atus`. Para regenerar este documento, ver
[`notebooks/calidad_datos.ipynb`](../notebooks/calidad_datos.ipynb) y el
script que lo produjo.

