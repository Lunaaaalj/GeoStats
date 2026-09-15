# Selección de variables — ATUS ZMM

Qué columnas conservar de las 51 de `atus_zmm.parquet` y con qué papel.
Decidido **solo sobre el [diccionario de datos](diccionario_de_datos.md)**; la
limpieza de cada campo se resuelve en la sanitización.

---

## Criterio

Las 51 columnas se parten en dos familias que no sirven para lo mismo:

| Familia | Describe | Existe | Papel |
|---|---|---|---|
| **Estructural** | El dónde y el cuándo | Siempre, haya accidente o no | Predictor del conteo |
| **Consecuente** | El accidente en sí | Solo después del hecho | Nunca predictor |

`TIPACCID`, los vehículos, las víctimas y los campos del conductor son
consecuentes: solo existen porque hubo un choque, así que no pueden explicar
cuántos choques habrá. Sirven para estratificar, para ser desenlace de un
modelo de severidad, y para el descriptivo.

---

## Núcleo — 16 columnas

Estructurales. Son las que entran a un modelo de conteo.

| Campo | Razón |
|---|---|
| `ID`, `ANIO`, `EDO`, `MPIO` | Llave real `(ANIO, EDO, MPIO, ID)`; sin ella no se detectan duplicados |
| `ANIO`, `MES`, `DIA` | Reconstruyen la fecha y definen el panel temporal |
| `DIASEMANA` | Señal limpia (viernes 205,946 vs domingo 170,507); 135 centinelas (0.01%) |
| `HORA` | Covariable temporal más informativa; 7 centinelas |
| `CVE_MUN` | Llave de unión al marco geoestadístico del INEGI |
| `NOM_MUN` | Etiqueta legible |
| `URBANA` | `1` = en intersección, `2` = no intersección. Ver nota abajo |
| `SUBURBANA` | Complemento excluyente de `URBANA` |
| `CALLE1`, `CALLE2` | Identifican la intersección; 0.28% y 3.40% de nulos |
| `LONGITUD`, `LATITUD` | Sin nulos, dentro del país, CRS documentado (EPSG:4326) |
| `CLASE` | Severidad en 3 niveles, verificada coherente con las víctimas |

> **`URBANA` no es un indicador de "urbano".** Sus códigos distinguen accidentes
> **en intersección** (1,157,890) de **no intersección** (130,043). Es la
> variable que permite separar el análisis de cruces del de tramos sin
> inventar nada. El diccionario ya reporta una inconsistencia a revisar:
> 20,389 registros marcados en intersección no traen `CALLE2`.

---

## Segundo anillo — 18 columnas

Consecuentes. Para el descriptivo y para definir estratos.

**`TIPACCID`** — taxonomía central del descriptivo. Única fuente sobre usuarios
vulnerables: `2` peatón (39,636), `10` motocicleta (160,646), `11` ciclista (13,683).

**Los 13 vehículos** — conservar en crudo, colapsar para análisis:

| Grupo | Campos |
|---|---|
| Ligero | `AUTOMOVIL`, `CAMPASAJ`, `CAMIONETA` |
| Vulnerable | `MOTOCICLET`, `BICICLETA` |
| Pesado | `CAMION`, `TRACTOR` |
| Transporte público | `PASCAMION`, `MICROBUS`, `OMNIBUS`, `TRANVIA` |
| Marginal | `FERROCARRI` (1,130), `TRANVIA` (331), `OTROVEHIC` |

`TRANVIA` y `FERROCARRI` serán prácticamente cero en la ZMM. Se conservan por
completitud, no por utilidad.

**`TOTMUERTOS`, `TOTHERIDOS`** — el diccionario verifica que cuadran exactamente
con sus componentes, sin excepción.

**`PEATMUERTO`, `PEATHERIDO`, `CICLMUERTO`, `CICLHERIDO`** — aparte de los
totales, porque peatones y ciclistas son la categoría central de cualquier
análisis de seguridad vial y no se recuperan del agregado.

---

## Con reservas — 5 columnas

Usables, con la advertencia documentada.

| Campo | Problema |
|---|---|
| `SEXO` | El código `1` no es un sexo: marca fuga del conductor (9.43%) |
| `EDAD` | 22.97% sin información (`0` fugado + `99` no especificado) |
| `ALIENTO` | 24.56% "se ignora"; que se hiciera la prueba no es aleatorio |
| `CAUSAACCI` | 95.3% dice "conductor". Varianza casi nula, atribución subjetiva |
| `CARRETERA` | 96.70% vacío; en la ZMM aplica al 1.5% de registros |

> Solo el **23.51%** de los registros tiene información completa en los seis
> campos con centinelas. Usarlos juntos con borrado de incompletos cuesta tres
> cuartas partes de la base.

---

## Descartar — 4 columnas

| Campo | Razón |
|---|---|
| `CINTURON` | **74.66% "se ignora"**. Solo 15% sí y 10% no. No recuperable |
| `CAPAROD` | 99.25% pavimentada; varianza cercana a cero |
| `MINUTOS` | `0` aparece 157,425 veces y `30` 119,320, contra ~10,000 de un minuto cualquiera. Es redondeo del capturista, no dato |
| `OTROMUERTO`, `OTROHERIDO` | 62 y 574 registros **a nivel nacional** |

> **`EDO` estaba aquí y se movió al núcleo.** Es cierto que queda constante = 19
> tras el recorte, pero la llave real es `(ANIO, EDO, MPIO, ID)`: sin él se rompe
> la detección de duplicados y cualquier `concat` contra la base nacional. Una
> columna constante en Parquet cuesta prácticamente cero.

> **Descartar no significa borrar del archivo.** `geostats.limpieza` produce un
> superconjunto: conserva las 51 columnas y agrega las derivadas. Esta lista se
> aplica al seleccionar para un análisis, no al escribir el parquet — así la
> decisión es reversible y auditable. Ver [`limpieza.md`](limpieza.md).

---

## Derivadas a construir

| Nueva | De | Para qué |
|---|---|---|
| `fecha` | `ANIO`+`MES`+`DIA` | Eje temporal; valida `DIASEMANA` |
| `ubicacion` | `URBANA`+`SUBURBANA` | Una categórica de 5 niveles en vez de dos columnas excluyentes |
| `en_interseccion` | `URBANA == 1` | Define el universo del análisis de cruces |
| `se_fugo` | `SEXO == 1` | Separa la fuga del sexo |
| `sexo_conductor` | `SEXO ∈ {2,3}` | Sexo limpio, con ausente explícito |
| `n_vehiculos` | Suma de los 13 | El diccionario garantiza que siempre es ≥ 1 |
| `id_punto` | `LONGITUD`+`LATITUD` | Llave estable del punto geocodificado |
| `hay_victimas` | `CLASE ∈ {1,2}` | Binaria para severidad |

> `EDAD = 0` y `SEXO = 1` marcan **exactamente los mismos registros** (verificado
> sobre 1.3M): son los accidentes con fuga. No es ruido, es estructura.

> **`id_cruce` se llama `id_punto`.** No todo punto es un cruce: en la ZMM hay
> 6,232 registros marcados explícitamente como *no* intersección y 6,578
> suburbanos. Tampoco se redondea: las coordenadas traen hasta ocho decimales y
> redondearlas fusiona puntos distintos. `limpieza` produce además un
> `id_punto_4d` con 10 m de tolerancia, para cuando se quiera agrupar por cruce.

---

## Resumen

```
51 columnas actuales
├── 16  núcleo          → estructurales, predictores del conteo
├── 18  segundo anillo  → consecuentes, descriptivo y estratos
├──  5  con reservas    → usables con advertencia
├──  4  descartar       → sin varianza o irrecuperables
└──  8  derivadas nuevas
```

39 de 51 conservadas, más 8 derivadas. El recorte es modesto: lo que importa no
es cuántas se tiran, sino **cuáles pueden ser predictores (16) y cuáles no**.

> **La implementación construyó 20 derivadas, no 8.** Estas ocho son las que este
> documento especificó desde el diccionario; `geostats.limpieza` agrega además
> las versiones sin centinela de los campos del conductor (`edad`,
> `aliento_alcoholico`, `cinturon`, `hora`, `dia_semana`), `gravedad`, las tres
> vialidades normalizadas, `falta_calle2`, `id_punto_4d` y `precision_baja`.
> La lista completa, con su regla y su porcentaje de nulos, está en
> [`limpieza.md`](limpieza.md).

**Alcance.** El diccionario advierte que la cobertura nacional crece de 91
municipios en 2019 a 198 en 2024. En la ZMM son los mismos 18 municipios los
seis años, así que ese sesgo no aplica aquí — pero impide comparar esta serie
con el agregado nacional.
