# Evaluaciones descartadas

Episodios completados de 120 s, de 3 por configuración salvo donde se indica.
"Sin evaluar" significa que no se llegó a probar en esa configuración.

| Carpeta | Genoma y evolución | C1 | C2 | C3 | Motivo |
|---|---|---|---|---|---|
| `candidato_id826` | 826, `inc_s2c_w40` gen. 31 | sin evaluar | 3/3 | 3/3 | Alternativa al 1038, que gira más suave y sí se evaluó en C1 |
| `candidato_id773` | 773, `inc_s2c_w40` gen. 29 | 3/3 | 2/3 | 1/3 | Mejor genoma antes de la etapa C3. Se acerca demasiado en las curvas |
| `candidato_id613` | 613, `inc_s2c_w40` gen. 26 | sin evaluar | 1/3 | sin evaluar | Choca a la salida de una curva |
| `candidato_id532` | 532, `inc_s2c_w40` gen. 19 | sin evaluar | 0/3 | sin evaluar | Evolucionado con 175 pasos. Choca con una señal en la tercera curva |
| `candidato_id297` | 297, `inc_s2c_w40` gen. 15 | sin evaluar | 1/6 | sin evaluar | Evolucionado con 175 pasos |
| `id404_wmax040` | 404, `inc_s2c_v30` gen. 15, evaluado con `w_max` 0,4 | 3/3 | 3/3 | 3/3 | Evolucionó con `w_max` 0,8. La escala se cambió solo al evaluarlo |
| `id404_filtro_tamano` | 404 con filtro del tamaño | sin evaluar | 0/3 | sin evaluar | El filtro no mejoró |
| `id404_tilt105` | 404 con tilt 105 | sin evaluar | 0/3 | sin evaluar | El tilt no mejoró |
| `s3_candidato_id971` | 971, `inc_s3c` gen. 37-39 | 0/3 | 0/3 | 1/3 | Mejor final de la semilla 3. En C1 llega demasiado rápido al guía lento y choca o lo pierde en 4-10 s |
| `s3_candidato_id918` | 918, `inc_s3c` gen. 35-36 | 0/3 | 1/3 | 0/3 | En C1 choca o pierde al guía en 5-6 s |
| `s3_candidato_id803` | 803, `inc_s3c` gen. 32-33 | 0/3 | 3/3 | 1/3 | En C1 se acerca, la pelota sale de la imagen por abajo y, sin ver, avanza a 0,13-0,15 m/s hasta chocar (48 s). En C3 la pierde en curva |
| `s3_candidato_id754` | 754, `inc_s3c` gen. 29 | sin evaluar | 3/3 | sin evaluar | Mejor de la semilla 3 antes de la etapa C3 |
| `s3_candidato_id236` | 236, `inc_s3c` etapa C1 | 3/3 | sin evaluar | sin evaluar | Mejor de la semilla 3 al terminar la etapa C1 |
| `historico` | Evaluaciones anteriores (ids 188, 544, 493, 238, 268, 77 y 404) | | | | Registros previos, con sus `episodios.csv` y `metricas.md` |

El 404 sin cambios, con `w_max` 0,8, completó 1/3 en C2 y 0/3 en C3. Esos
registros están en `historico`.
