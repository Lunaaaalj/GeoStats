# Prototipo: relieve 3D de la ZMM

Prueba de concepto para decidir si un relieve hexagonal entra a la
presentación. **No es un producto**: no está enlazado desde ningún lado y
puede borrarse sin romper nada.

```bash
PYTHONPATH=$PWD/src uv run python docs/prototipo_3d/construir.py
open docs/prototipo_3d/relieve_3d.html
```

`construir.py` incrusta los datos dentro del HTML en lugar de cargarlos con
`fetch`, para que el archivo abra directo desde el disco: el navegador bloquea
las peticiones `file://` a un JSON vecino.

## Las dos vistas

| Vista | Altura | Qué responde |
|---|---|---|
| Accidentes esperados 2027 | `lambda_med` | Dónde habrá más hechos de tránsito |
| Relativo a su municipio | `exp(uᵢ)` | Dónde hay más riesgo *dentro de cada municipio* |

La segunda se calcula dividiendo `lambda_med` entre la media geométrica de su
municipio. Como `lambda_med = exp(β₀ + m_j + uᵢ)` y `(β₀ + m_j)` es constante
dentro de un municipio, esa división deja exactamente `exp(uᵢ − media_j(u))`:
el perfil espacial del modelo, limpio del régimen de reporte. No hace falta
volver a muestrear el modelo para obtenerla.

Conmutar entre las dos anima la transición de alturas. Ese contraste es el
argumento del prototipo: en la primera vista los municipios aparecen como
bloques (Guadalupe hundido porque dejó de capturar); en la segunda los bloques
desaparecen y quedan los corredores.

## Estado desde la URL

Para enlazar una vista concreta sin tocar los controles en vivo:

| Hash | Efecto |
|---|---|
| `#rel` | Abre en la vista relativa |
| `#log` | Altura en escala logarítmica |
| `#opac` | Translucidez donde hay pocos datos |
| `#persp` | Proyección en perspectiva (por defecto es ortográfica) |
| `#sinvias` | Oculta las vialidades |

Se combinan con comas: `relieve_3d.html#rel,log`.

## Decisiones que conviene no deshacer

- **deck.gl, no CSS 3D.** CSS ordena por elemento, sin búfer de profundidad:
  con 2,241 prismas habría celdas pintadas delante de otras que deberían
  taparlas, y el criterio varía entre navegadores.
- **Proyección ortográfica por defecto**, para que dos celdas iguales midan
  igual estén cerca o lejos de la cámara.
- **El color va en escala logarítmica** aunque la altura sea lineal. La
  leyenda lo declara; sin eso el 80 % del mapa sale del mismo tono.
- **La nota de la esquina no es decorativa.** La vista absoluta incluye el
  régimen de reporte municipal, y eso hay que decirlo donde se ve el mapa.

## Fuentes

- `data/processed/pronostico_2027_geo.parquet` — lo produce `pronostico_2027.qmd`
- `docs/presentacion/vialidades_zmm.json` — contexto vial, ya en EPSG:4326
