# Material para la defensa (no se entrega)

Pruebas anteriores al controlador final, para enseñarlas en la defensa o
usar sus figuras y comparativas en la memoria.

| Carpeta | Contenido |
|---|---|
| `evoluciones/` | Formulaciones anteriores de la calidad y semilla 8 de la configuración final ([README](evoluciones/README.md)) |
| `p2_eval/` | Evaluaciones de esas evoluciones y de candidatos descartados ([README](p2_eval/README.md), [C4](p2_eval/c4/README.md)) |
| `config_descartadas/` | Configuraciones de las formulaciones anteriores (`config_c4_dir.json`, `config_c4_parada.json`) y de pruebas |
| `figuras/` | Figuras de las evoluciones anteriores (semilla 2 incremental, semilla 3, C1) |
| `xor/` | Prueba de NEAT-Python con el XOR de las indicaciones |
| `reevaluar.py` | Reevaluación de los mejores genomas de una evolución; para usarlo, copiarlo a la raíz del repositorio |

## Formulaciones

| | Evolución | Carpeta | Mejor controlador |
|---|---|---|---|
| F1 | Incremental C1 → C3 (banda 0,25-0,45 m) | `evoluciones/inc_s2c_w40`, `inc_s2c_w40_c4`, `inc_s3c` | 1038: C1-C3 9/9, C4 0/2 |
| F2 | Desde cero en C4, banda 0,30-0,45 m | `evoluciones/dir_c4_s5` | 557: C4 3/3, C3 1/3 |
| F3 | F2 + término de parada con penalización | `evoluciones/dir_c4p_s6`, `dir_c4p_s7` | No aprende |
| F4 | Final (entregada) | `../evoluciones/semilla6`, `semilla7`, `semilla9` y aquí `evoluciones/dir_c4f_s8` | 437 |

La semilla 8 de la configuración final no aprendió (mejor calidad 15 en la
generación 24).

## Nombres antiguos

Los README de `evoluciones/` y `p2_eval/` se escribieron antes de reorganizar
el repositorio y usan los nombres antiguos de las carpetas entregadas:

| Antes | Ahora |
|---|---|
| `evoluciones/dir_c4f_s6`, luego `final_s6` | `../evoluciones/semilla6` |
| `evoluciones/dir_c4f_s7` | `../evoluciones/semilla7` |
| `evoluciones/dir_c4f_s9` | `../evoluciones/semilla9` |
| `p2_eval/semilla6_c4f_id437` y `p2_eval/c4/c4f_s6_id437` | `../p2_eval/controlador_final_s6_id437` |
| `p2_eval/c4/c4f_id276` | `../p2_eval/controlador_s7_id276` |
| `p2_eval/c4/c4f_s9_id313` | `../p2_eval/controlador_s9_id313` |

Las evaluaciones del 310, el 376 y el 193 (`p2_eval/c4/c4f_s6_id*`,
`prueba_id193`) son genomas de la semilla 6 y conservan en sus ficheros el
nombre `p2_dir_c4f_s6`.

Para dibujar las curvas de estas evoluciones desde la raíz:

```bash
python3 curvas_p2.py --etiquetas ../defensa/evoluciones/inc_s2c_w40 --por-config --salida defensa/figuras/evolucion_s2.png
```
