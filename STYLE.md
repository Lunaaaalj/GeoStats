# Guía de estilo — GeoStats

Reglas de redacción para todo texto del repositorio: documentación de `docs/`,
prosa de los notebooks `.qmd`, reporte técnico en LaTeX, docstrings,
comentarios, mensajes de commit y descripciones de PR. Aplica por igual a
colaboradores y a agentes. Lo que esta guía no cubre lo resuelve la
convención ya presente en el archivo que se edita.

La identidad visual de las gráficas está en el [README](README.md) y en
`CLAUDE.md` § "Gráficas"; no se repite aquí.

## Principios

La redacción es **técnica, impersonal y densa**.

- **Técnica.** Cada afirmación es verificable: lleva una cifra, una
  referencia a código, a un notebook o a una fuente. Se usa el término
  preciso aunque exista uno más coloquial.
- **Impersonal.** El sujeto es el dato, el método o el artefacto, no quien
  escribe. Sin primera persona, singular ni plural.
- **Densa.** Cada oración aporta información nueva. Se elimina todo lo que
  pueda borrarse sin perder contenido.

## Voz y persona

| Evitar | Usar |
|---|---|
| Encontramos que el 64.4 % de las defunciones… | El 64.4 % de las defunciones… |
| Decidimos usar hexágonos porque… | Se eligió la rejilla hexagonal porque… |
| Vemos en la gráfica que… | La figura 3 muestra… |
| Nuestro modelo predice… | El modelo jerárquico predice… |
| Puedes regenerar el archivo con… | El archivo se regenera con… |

- Preferir, en este orden: sujeto no humano en voz activa ("la rejilla
  elimina el sesgo de frontera") › pasiva refleja ("se descartó el AGEB") ›
  pasiva perifrástica ("fue descartado"), esta última solo si las anteriores
  fuerzan una construcción ambigua.
- Instrucciones (comandos, pasos de reproducción): infinitivo o pasiva refleja
  ("Ejecutar `uv sync`", "se ejecuta `uv sync`"), nunca imperativo de
  segunda persona ("ejecuta").
- Excepción acotada: el bloque introductorio del `README.md` es material de
  divulgación y admite tono más directo. Sus secciones técnicas siguen esta
  guía.

## Densidad

- **Sin preámbulos ni cierres.** Prohibido: "En esta sección se
  presentará…", "Como se mencionó anteriormente…", "Es importante señalar
  que…", "En conclusión…". La sección empieza con su primer hecho.
- **Sin intensificadores ni adjetivos valorativos**: *muy*, *bastante*,
  *claramente*, *significativamente* (salvo en sentido estadístico, con su
  prueba y valor *p*), *interesante*, *robusto* (salvo en sentido técnico),
  *crucial*, *clave*.
- **Cuantificar en lugar de calificar.** No "la mayoría de los accidentes
  ocurren en intersecciones", sino "366,484 de 379,294 accidentes (96.6 %)
  ocurren en intersecciones".
- **Una idea por oración; un tema por párrafo.** La primera oración del
  párrafo enuncia la conclusión; las siguientes la sostienen.
- **Explicar el porqué, no solo el qué.** Una decisión de diseño se
  documenta con la alternativa descartada y la razón ("Se descartó
  `dropna()`: con faltante MNAR sesga contra los accidentes graves").
- **No repetir.** Si un hecho está documentado en otro archivo, se enlaza
  (`ver docs/limpieza.md § "El principio"`) en vez de reescribirlo.
- Listas y tablas en lugar de prosa cuando el contenido es enumerable o
  comparable; prosa cuando hay una cadena causal.

## Precisión

- **Afirmaciones con evidencia.** Toda cifra procede de un cálculo
  reproducible del repositorio o de una fuente citada. No se redondea para
  impresionar ni se omite el denominador.
- **Causalidad.** Los datos son observacionales: se escribe "se asocia con",
  "coincide con", "concentra", no "causa" ni "provoca", salvo que el diseño
  lo justifique explícitamente.
- **Incertidumbre explícita.** Estimaciones con su intervalo y nivel
  (forma: `estimación [IC 90 %: inferior–superior]`); pronósticos con su horizonte y
  supuestos.
- **Límites declarados.** Lo que el dato no permite concluir se dice en el
  mismo lugar que la conclusión, no en una sección aparte de limitaciones
  que nadie lee. Ejemplo: el salto 2020→2021 del panel nacional es
  cobertura, no siniestralidad.
- **Lenguaje no especulativo.** Sin "probablemente", "parece que" ni "podría
  deberse a" sin una hipótesis contrastable o una referencia.

## Terminología

- **Idioma**: español en todo el repositorio, incluidos commits,
  comentarios y nombres de funciones y variables.
- **Anglicismos**: se usa el término en español cuando existe y es de uso
  técnico corriente (*rejilla*, no *grid*; *conjunto de datos* o *base*, no
  *dataset*; *faltante*, no *missing*). Si no existe equivalente
  establecido, el término inglés va en cursiva la primera vez y, si
  conviene, con su traducción entre paréntesis (*flat-top*, *notebook*,
  *pipeline*). Las siglas técnicas establecidas se conservan en inglés
  (MNAR, MAR, MAUP, CRS, STL, UTM).
- **Siglas**: se desarrollan en su primera aparición en cada documento,
  "Zona Metropolitana de Monterrey (ZMM)"; después, solo la sigla. Sin
  plural con *s* ("los AGEB", no "los AGEBs").
- **Glosario del proyecto** (usar siempre la misma forma):

  | Término | Uso |
  |---|---|
  | accidente | Unidad de registro de ATUS. *Hecho de tránsito* solo en material de divulgación. |
  | ZMM | Los 18 municipios de `zonas.ZMM_MONTERREY`. |
  | celda, hexágono | Unidad de la rejilla de `espacial.celdas()`. |
  | centinela | Código que representa un faltante (`99`, `0`, etc.); no se llama "nulo". |
  | faltante | Ausencia de dato, codificada o `NaN`. |
  | derivada | Columna construida por el repo (minúsculas). |
  | crudo / procesado | Contenido de `data/raw/` / `data/processed/`. |

- **Columnas y código** siempre en formato de código: `CVE_MUN`,
  `atus_zmm.parquet`, `espacial.celdas()`. Los nombres de columna
  conservan su capitalización original (`MAYÚSCULAS` del INEGI,
  `minúsculas` derivadas).

## Números y unidades

- **Separador decimal: punto. Separador de miles: coma.** `379,294`,
  `92.9 %`, `0.65 km²`. Los años y claves no llevan separador (`2024`,
  `19039`).
- **Porcentaje con espacio** (no separable) antes del signo: `92.9 %`; en
  LaTeX, `92.9\,\%`.
- **Unidades del SI** con espacio: `500 m`, `13.5 MB`; en LaTeX `500\,m`.
- **Rangos** con guion medio (–), sin espacios: `2019–2024`,
  `70,800–77,600`. Los cambios entre periodos con flecha: `2020→2021`.
- **Cifras significativas**: porcentajes a un decimal salvo que el
  contexto exija más; coeficientes y estadísticos a dos o tres cifras
  significativas, iguales en toda una tabla.
- Números del cero al nueve con letra en prosa cuando no son medidas
  ("tres razones", "seis vecinos"); con cifra si llevan unidad o forman
  parte de una serie comparable ("6 años, 18 municipios, 2,241 celdas").

## Estructura de los documentos

- **Encabezado H1** con el nombre del documento; inmediatamente después,
  un párrafo de una a tres oraciones que dice qué cubre el documento y qué
  no, con enlaces a los documentos vecinos.
- **Encabezados** en mayúscula inicial y sin punto final ("Las 22 columnas
  derivadas", no "Las 22 Columnas Derivadas."). Que el encabezado diga el
  contenido, no la categoría ("El faltante es MNAR" mejor que
  "Observaciones").
- **Énfasis**: negritas solo para la regla o el hallazgo principal de un
  bloque, como máximo una o dos por párrafo. Cursivas para términos en
  otro idioma y para introducir un término definido.
- **Enlaces relativos** a archivos del repositorio; referencias a
  secciones con `§ "Título de la sección"`.
- **Bloques de código** con lenguaje declarado (` ```bash `, ` ```python `)
  y comentarios que indiquen el efecto del comando, no su sintaxis.
- **Figuras y tablas** numeradas en el reporte y en los `.qmd`; todo
  `alt`/pie de figura describe qué muestra la gráfica (tipo y variables),
  no la conclusión.
- Sin emojis fuera del bloque de divulgación del `README.md`.

## Por tipo de artefacto

### Documentación (`docs/*.md`)

Referencia técnica: qué hace cada componente, qué decide no hacer y por
qué. Se actualiza en el mismo commit que el código que describe.

### Notebooks (`notebooks/*.qmd`)

- La prosa entre celdas interpreta el resultado de la celda anterior con
  cifras concretas; no narra el código ("A continuación se carga…").
- Cada notebook abre con la pregunta que contesta y cierra con una sección
  de hallazgos en forma de lista, cada uno con su cifra.
- Los valores citados en prosa se generan con código en línea
  (`` `{python} valor` ``) siempre que sea posible, para que no queden
  desactualizados tras un re-render.

### Reporte técnico (`docs/reporte/`)

- Registro académico: mismas reglas, más citas (`\cite{}`) para todo
  método no estándar y para toda afirmación externa al repositorio.
- Referencias cruzadas con `\ref{}` y etiquetas con prefijo de tipo
  (`sec:`, `fig:`, `tab:`, `eq:`).
- Notación matemática definida en su primera aparición; un mismo símbolo
  no se reutiliza con dos significados.

### Código (docstrings y comentarios)

- Docstring de una línea con el efecto de la función en tercera persona
  ("Devuelve la rejilla…", "Falla si…"); detalles debajo, solo si añaden
  información que la firma no da.
- Los comentarios explican el porqué o el dato no obvio ("CP1252 no
  define 0x81; se lee con latin-1"), nunca repiten lo que el código dice.

### Commits y PR

- Conventional Commits en español, en minúsculas y en presente de
  indicativo, tercera persona: `feat(zonas): agrega el recorte a la ZMM`,
  `docs(datos): documenta los centinelas de EDAD`. Asunto de 72 caracteres
  como máximo, sin punto final.
- El cuerpo explica el motivo y el efecto del cambio, no la lista de
  archivos tocados.
- Descripción de PR: qué cambia, por qué, cómo se verificó.

## Lista de verificación

Antes de dar por terminado un texto:

1. ¿Hay alguna primera o segunda persona? Reescribir.
2. ¿Alguna oración puede borrarse sin perder información? Borrarla.
3. ¿Cada adjetivo valorativo o cuantificador vago tiene una cifra detrás?
4. ¿Las cifras siguen el formato de § "Números y unidades"?
5. ¿Las siglas están desarrolladas en su primera aparición?
6. ¿Las decisiones citan la alternativa descartada y la razón?
7. ¿Lo ya documentado en otro archivo está enlazado y no repetido?
