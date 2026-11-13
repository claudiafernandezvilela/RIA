# Práctica 2 · Neuroevolución con NEAT

Controlador del seguidor de "Follow City" (RoboboSim) evolucionado con
NEAT-Python sobre el entorno de la P1.

**Controlador final: id 437, semilla 6**
(`evoluciones/semilla6/controlador_final_s6_id437.pkl`). Es un único
controlador para C1-C4: completa los 11 episodios de la evaluación
(3 en C1, C2 y C3; 2 en C4, como pide el anexo B).

## Archivos

| Archivo | Qué es |
|---|---|
| `evolucionar.py` | Bucle de evolución: crea la población, evalúa cada genoma en el simulador, guarda puntos de control y una fila por generación |
| `calidad.py` | Función de calidad (`python3 calidad.py` la comprueba con episodios inventados, sin simulador) |
| `env.py` | Entorno de la P1 (`RoboboSeguirEnv`): observación, acción, fin de episodio y lectura del simulador |
| `evaluar.py` | Evaluación con el protocolo del anexo B (`--genoma`) y tablas de métricas (`--metricas`) |
| `curvas_p2.py` | Curvas de calidad y especiación a partir de `evolucion.csv` |
| `red_p2.py` | Figura de la topología de un genoma y lista de sus conexiones |
| `config.json` | Configuración base del entorno (calibración, límites, umbrales del anexo B) |
| `config_c4_final.json` | Configuración final del entorno y de la calidad, aplicada sobre `config.json` |
| `config-p2.ini` | Configuración de NEAT (6 entradas, 2 salidas, población 20) |
| `evoluciones/` | Las tres semillas de la configuración final |
| `p2_eval/` | Evaluación de los mejores controladores de cada semilla |
| `figuras/` | Figuras de la memoria |
| `memoria/` | Memoria de la P2 |

## Semillas y controladores

Las tres semillas usan la misma configuración (`config_c4_final.json`). Se
evolucionaron desde cero con el guía en C4: 25 generaciones, población 20 y
2 episodios de 200 pasos por individuo.

| Semilla | Evolución | Controlador | Evaluación | Completa | En banda | Paradas superadas en C4 |
|---|---|---|---|---|---|---|
| 6 | `evoluciones/semilla6/` | **`controlador_final_s6_id437.pkl`** (final) | `p2_eval/controlador_final_s6_id437/` | **C1-C4: 11/11** | **73,7 %** | 9 de 10 |
| 7 | `evoluciones/semilla7/` | `controlador_s7_id276.pkl` | `p2_eval/controlador_s7_id276/` | C1-C4: 11/11 | 67,0 % | 9 de 11 |
| 9 | `evoluciones/semilla9/` | `controlador_s9_id313.pkl` | `p2_eval/controlador_s9_id313/` | C4: 2/2 | 60,4 % | 9 de 13 |

- "En banda": porcentaje de pasos con la separación entre 0,20 y 0,45 m.
- No se cuentan las paradas que ocurren al final del episodio, sin los 10 s
  de margen para comprobarlas.
- Cada controlador es una copia del mejor genoma de su evolución:
  - el 437 es `genomas/mejor_gen024.pkl` de la semilla 6;
  - el 276 es `genomas/mejor_gen024.pkl` de la semilla 7;
  - el 313 es `genomas/mejor_gen022.pkl` de la semilla 9, el mejor en las
    generaciones 19, 20 y 22.
- El 437 es el final porque es el que mejor mantiene la separación
  objetivo y el que se detiene en más paradas del guía.

Contenido de cada carpeta de `evoluciones/`:

| Fichero | Contenido |
|---|---|
| `config-p2.ini` | Configuración de NEAT, con la semilla |
| `entorno.json` | Configuración del entorno usada en la evolución |
| `evolucion.csv` | Una fila por generación (calidad, especies, coste) |
| `genomas/mejor_genNNN.pkl` | Mejor genoma de cada generación |
| `chk/p2-N` | Punto de control: población antes de la generación N |
| `episodios_individuo.txt` | Episodios por individuo |
| `consola.log` | Salida de la consola durante la evolución |

## Antes de empezar

- Puente ROS 2 con el módulo `sim` (sin él no hay separación real y la
  calidad no se puede calcular):

  ```bash
  ros2 run robobo_ros2 robobo_container --ros-args -p ip:=host.docker.internal -p modules:="['blob','sim']"
  ```
- El guía se pone **a mano** en RoboboSim; `--guia` / `--config` solo lo
  anotan. C4 es Variable 10-40 con `Stop times` 2-5 s y `Stop chances` 60.
- **RoboboSim en primer plano** durante la evolución y la evaluación. Con la
  ventana en segundo plano o la pantalla apagada el simulador se comporta
  distinto y los resultados no valen.

## Reproducir la evolución

Los valores por defecto de `evolucionar.py` son los de la configuración
final. Con una etiqueta nueva:

```bash
python3 evolucionar.py --etiqueta repeticion_s6 --guia c4 --semilla 6
```

Si se corta, relanzar el puente y continuar desde el último punto de control
(`--generaciones` es el total):

```bash
python3 evolucionar.py --etiqueta repeticion_s6 --guia c4 --reanudar
```

NEAT-Python es reproducible con la semilla, pero el simulador no: dos
evoluciones con la misma semilla no dan la misma población.

## Ejecutar y evaluar el controlador final

Con el guía en la configuración indicada (`c1`, `c2`, `c3` o `c4`):

```bash
python3 evaluar.py --genoma evoluciones/semilla6/controlador_final_s6_id437.pkl --config c4 --episodios 2 --carpeta p2_eval/controlador_final_s6_id437
python3 evaluar.py --metricas --carpeta p2_eval/controlador_final_s6_id437
```

`evaluar.py` añade los episodios a los que ya haya en la carpeta.

## Figuras

```bash
python3 curvas_p2.py --etiquetas semilla6 --salida figuras/evolucion_semilla6.png
python3 curvas_p2.py --etiquetas semilla7 --salida figuras/evolucion_semilla7.png
python3 curvas_p2.py --etiquetas semilla9 --salida figuras/evolucion_semilla9.png
python3 curvas_p2.py --etiquetas semilla6 semilla7 semilla9 --salida figuras/evolucion_semillas.png
python3 red_p2.py --genoma evoluciones/semilla6/controlador_final_s6_id437.pkl --salida figuras/red_437.png
```
