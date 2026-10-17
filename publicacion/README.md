# Publicación — carrusel de Instagram

Veinte láminas verticales de **1080 × 1350** (4:5). Diecinueve se generan aquí;
la 15 la ponen los autores y la numeración ya le deja su lugar:

| # | Lámina | Origen |
|---|---|---|
| 01 | Portada | `01_portada.png` |
| 02 | Nota periodística | `02_nota_periodistica.png` |
| 03 | Por qué hicimos esto | `03_por_que.png` |
| 04 | La problemática (lámina 4 de la presentación) | `04_la_problematica.png` |
| 05 | De dónde salen los datos (lámina 6) | `05_los_datos.png` |
| 06 | Heridos y defunciones, con mapa | `06_heridos_y_defunciones.png` |
| 07 | Grupos vulnerables | `07_grupos_vulnerables.png` |
| 08 | Calendario hora × día | `08_hora_y_dia.png` |
| 09 | Es de corredor, no de esquina | `09_corredores.png` |
| 10 | Dónde cuestan vidas (flujo) | `10_costo_humano.png` |
| 11 | Mil cruces explican el 40 % (tabla) | `11_concentracion.png` |
| 12 | Tienen nombre y apellido | `12_nombre_y_apellido.png` |
| 13 | La tendencia en seis años | `13_tendencia.png` |
| 14 | Pronóstico 2027 y municipios con más riesgo | `14_pronostico_2027.png` |
| 15 | Foto de la app | **la proveen los autores** |
| 16 | Reflexiones | `16_reflexiones.png` |
| 17 | Transición: revisa la info por ti mismo | `17_revisalo_tu.png` |
| 18 | QR del visor | `18_qr_visor.png` |
| 19 | QR del repositorio | `19_qr_repositorio.png` |
| 20 | QR de la presentación | `20_qr_presentacion.png` |

## Regenerar

```bash
uv run --with segno --with playwright --no-project python publicacion/construir.py
```

Usa el Chrome instalado (`channel="chrome"`), así que no descarga navegadores.
Se edita `plantilla.html`; los PNG **se generan**.

## Cómo está armado

No hay datos propios: todo sale de `docs/presentacion/datos.json`, con las
mismas fuentes, logotipos y generador de QR (`construir.py` importa el de la
presentación). Si cambia `datos.json`, basta con volver a correr el script.

`logos/` guarda las imágenes propias del carrusel y tienen prioridad sobre las
de la presentación: el recorte de la nota periodística y el logotipo nuevo de
SDLM (fondo transparente, para invertirlo sobre la portada oscura).

- Solo la portada lleva el logotipo de SDLM; todas las demás llevan el de
  GeoStats arriba a la derecha (lo agrega el script) y el número de lámina
  abajo a la izquierda.

- Lo observado va en la rampa fría y lo estimado (2027) en la cálida, igual que
  en la presentación.
- Los seis mapas anuales de la lámina 13 comparten la misma escala de color;
  si no, 2020 se vería tan intenso como 2024.
- "Zonas en el 5 % peor" (lámina 14) cuenta las zonas con probabilidad ≥ 50 %
  de estar en el 5 % de mayor riesgo: son las 112 que reporta el modelo.
