# Limpieza — ATUS ZMM

Qué hace `geostats.limpieza` con `atus_zmm.parquet` y qué decide **no** hacer.
379,294 registros, **51 columnas → 73**; las 51 originales salen intactas.

```bash
uv run limpiar-atus          # data/processed/atus_zmm_limpio.parquet   (13.5 MB)
uv run limpiar-atus --geo    # además el GeoParquet                     (16.0 MB)
```

## El principio

**Nunca borra filas y nunca imputa.** Solo agrega columnas y banderas. El
faltante de esta base es **MNAR**: en accidentes fatales el aliento alcohólico se
ignora 2.4 veces más seguido que en los de solo daños
([`calidad_datos.qmd`](../notebooks/calidad_datos.qmd)). Con ese mecanismo
`dropna()` sesga contra los accidentes graves e imputar bajo supuesto MAR mete
sesgo en silencio. El artefacto limpio es un **superconjunto**: lo que se tire,
se tira al analizar.

Nombres: `MAYÚSCULAS` = tal como llegó del INEGI, nunca se modifica;
`minúsculas` = construido por este repo. Excepción: `CVE_MUN` y `NOM_MUN`, que
siguen la nomenclatura de claves geoestadísticas del INEGI.

## Las 22 columnas derivadas

| Columna | Tipo | Regla | NA |
|---|---|---|---|
| `fecha` | `datetime64` | `ANIO`+`MES`+`DIA`; cubre 2019-01-01 a 2024-12-31 | 0 |
| `hora` | `Int8` | `HORA`, con `99` → NA | 0 |
| `dia_semana` | `category` ord. | `DIASEMANA` → nombre, con `8` → NA | 0 |
| `se_fugo` | `bool` | `SEXO == 1` | 36,973 `True` |
| `sexo_conductor` | `category` | `2`→Hombre, `3`→Mujer; `1` → NA | 9.75 % |
| `edad` | `Int16` | `EDAD`, con `0` y `99` → NA | 27.86 % |
| `aliento_alcoholico` | `boolean` | `4`→sí, `5`→no; `6` → NA | 14.67 % |
| `cinturon` | `boolean` | `7`→sí, `8`→no; `9` → NA | 72.25 % |
| `ubicacion` | `category` | `URBANA`+`SUBURBANA` en 5 niveles | 0 |
| `en_interseccion` | `bool` | `URBANA == 1` | 366,484 `True` |
| `n_vehiculos` | `int16` | Suma de los 13 conteos; 1 a 10, media 1.89 | 0 |
| `gravedad` | `category` ord. | `CLASE` → Fatal ‹ No fatal ‹ Solo daños | 0 |
| `hay_victimas` | `bool` | `CLASE ∈ {1,2}` | 21,523 `True` |
| `calle1_norm` | `string` | Recorte, espacios, mayúsculas, sin acentos | 0.11 % |
| `calle2_norm` | `string` | Igual | 1.58 % |
| `calle1_hom` | `string` | `calle1_norm` homologada: sin genérico ni abreviatura, con alias verificados | 0.11 % |
| `calle2_hom` | `string` | Igual, desde `calle2_norm` | 1.58 % |
| `carretera_norm` | `string` | Igual | 98.51 % |
| `falta_calle2` | `bool` | `en_interseccion` y `calle2_norm` en NA | 3,072 `True` |
| `id_punto` | `string` | `"lon,lat"` exacto, vía `str(float)` | 0 |
| `id_punto_4d` | `string` | `"lon,lat"` a 4 decimales (~10 m) | 0 |
| `precision_baja` | `bool` | Los **dos** ejes con ≤ 3 decimales | 3 `True` |

### Las decisiones que no se leen solas

**El INEGI no usa nulos**: codifica la ausencia como valor válido del catálogo,
así que `isna()` sobre las originales devuelve cero y aun así falta hasta el 72 %
del dato. Las derivadas son las que hacen que `isna()` diga la verdad, y las
originales se conservan porque «se fugó» y «se ignora» son mecanismos distintos:
`SEXO = 1` y `EDAD = 0` marcan los mismos 36,973 registros. Por lo mismo no hay
timestamp completo: `MINUTOS` concentra la quinta parte de la base en `0` y `30`.

**`id_punto` usa `str(float)`, no un formato fijo.** Las coordenadas traen hasta
ocho decimales y formatearlas a seis fusiona **8,115 puntos distintos** en
silencio. `id_punto_4d` tolera 4 decimales y no 3 porque a 25.7 N son ~10 m,
mientras que 3 serían ~100 m y la manzana en Monterrey mide eso. El 72.3 %
comparte coordenada exacta con otro registro (131,180 puntos distintos, 54,742
con 10 m de tolerancia): conviven nodos de catálogo y geocodificación individual.

**La normalización vive solo en la derivada**, porque los acentos son parte del
nombre real; `Ñ` → `N` es una fusión real y por eso no toca el original.
`falta_calle2` separa el hueco real del estructural: la segunda vialidad debe
estar *en* intersección.

**`_hom` es la columna para contar vialidades; `_norm`, para todo lo demás.**
El mismo parte escribe «AVENIDA PASEO DE LOS LEONES», «PASEO DE LOS LEONES» o
«AV.PASEO DE LOS LEONES»: contadas por `_norm` son tres calles y el ranking de
avenidas sale partido. La homologación separa el punto pegado, repone el punto
de la inicial («MANUEL L BARRAGAN»), expande `AV`/`AVE`/`BLVD`/`CALZ`… y quita
el genérico `AVENIDA`, `CALLE`, `BOULEVARD` o `CALZADA`. Se comprobó con la
geometría: `AVENIDA X` y `X` caen a menos de 100 m una de otra en el 98.5 % de
los registros y `CALLE X` en el 95.8 %. `CARRETERA` no se quita porque ahí baja
a 70 % («CARRETERA NACIONAL» no es la calle «NACIONAL»). Los nombres distintos
pasan de **28,173 a 19,474**.

Los títulos **no** se quitan por regla, porque distinguen calles reales:
«GENERAL LAZARO CARDENAS» está entero en Guadalupe y «LAZARO CARDENAS» en
Monterrey y San Pedro; «ELEUTERIO GONZALEZ» está en Santiago y no es Gonzalitos.
Las formas cortas y largas se unen solo con `ALIAS_VIALIDAD`, diez alias
escritos a mano, y cada uno entra si al menos el 75 % de sus registros cae a
menos de 100 m del nombre canónico. «LEONES» a secas se quedó fuera con 74.8 %.
Caso límite aceptado: «CALLE CALZADA SUR» (un registro) queda como «SUR».

## Lo que decide no hacer

| No hace | Por qué |
|---|---|
| Imputar | El faltante es MNAR; imputar bajo MAR mete sesgo silencioso |
| Borrar filas | Solo el 25.5 % está completo en los seis campos clave |
| Tirar columnas | Es un superconjunto; se selecciona al analizar ([`seleccion_datos.md`](seleccion_datos.md)) |
| *Jitter* en coordenadas | Decisión de análisis; un archivo con ruido inyectado es una mentira para cualquier otro uso |
| Quitar títulos (`GENERAL`, `DOCTOR`) por regla | Fusiona calles distintas de municipios distintos; solo hay alias verificados uno por uno |
| Pegar la tasa de captura al renglón | Es un agregado: al filtrar deja de significar lo que dice. Vive como función |

## Verificación

`validar()` recorre **23 invariantes** y lanza excepción con la lista de las que
fallen; las diez primeras son las de `calidad_datos.qmd`, que dieron cero
violaciones sobre la base sucia, así que si aparecen ahora la limpieza rompió
algo. `diagnostico()` reporta, sin reprobar, catorce cifras más.

`tasa_captura(datos, campo)` da el porcentaje con dato real por municipio y año.
El faltante de `CINTURON`, `ALIENTO` y `EDAD` mide **práctica administrativa, no
conducta vial**: va de 10.4 % en San Pedro a 100 % en Monterrey, y Guadalupe
salta de 20.3 % a 96.8 % en un año. Comparar municipios o años exige esta tabla.

## Correcciones a los documentos previos

- **El hallazgo 11 de calidad de datos sobreestima el problema**: sus «866
  registros con ≤ 3 decimales» miran solo longitud; por ambos ejes son **3**.
- **`EDO` no se descarta** pese a `seleccion_datos.md`: es constante = 19, pero
  la llave real es `(ANIO, EDO, MPIO, ID)`.
- **`id_cruce` se llama `id_punto`**: no todo punto es un cruce (6,232 no lo son).
