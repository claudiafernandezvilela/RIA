# Práctica 2 · Neuroevolución con NEAT

Controlador del seguidor evolucionado con NEAT-Python sobre el mismo entorno
de la P1. **Controlador final: id 437**
(`evoluciones/dir_c4f_s6/genomas/mejor_gen024.pkl`), un único controlador
para C1-C4 (12/12 episodios completados).

## Archivos

| Archivo | Qué es |
|---|---|
| `evolucionar.py` | Bucle de evolución: crea la población, evalúa cada genoma en el simulador, guarda puntos de control y una fila por generación |
| `calidad.py` | Función de calidad (`python3 calidad.py` la comprueba con episodios inventados, sin simulador) |
| `config-p2.ini` | Configuración de NEAT (6 entradas, 2 salidas, población 20) |
| `config_c4_final.json` | Configuración final del entorno y de la calidad, aplicada sobre `config.json` |
| `config_c4_dir.json`, `config_c4_parada.json` | Configuraciones de formulaciones anteriores (ver `evoluciones/README.md`) |
| `env.py` | Entorno de la P1 (`RoboboSeguirEnv`): observación, acción, fin de episodio y lectura del simulador |
| `config.json` | Configuración base del entorno (calibración, límites, umbrales del anexo B) |
| `evaluar.py --genoma` | Evaluación con el protocolo del anexo B |
| `curvas_p2.py` | Curvas de calidad y especiación a partir de `evolucion.csv` |
| `red_p2.py` | Figura de la topología de un genoma y lista de sus conexiones |
| `reevaluar.py` | Reevalúa los mejores genomas de una evolución (pruebas) |
| `evoluciones/<etiqueta>/` | Cada evolución: configuración, CSV, mejores genomas y puntos de control ([README](evoluciones/README.md)) |
| `p2_eval/` | Registros y métricas de la evaluación ([README](p2_eval/README.md)) |
| `xor/` | Prueba de NEAT-Python con el XOR de las indicaciones |
| `memoria/` | Memoria de la P2 |
| `p1/` | Práctica 1, ya entregada ([README](p1/README.md)) |

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

## Reproducir la evolución final

Los valores por defecto de `evolucionar.py` son los de la configuración final
(`config_c4_final.json`, episodios de 200 pasos, 2 episodios por individuo,
25 generaciones, población 20):

```bash
python3 evolucionar.py --etiqueta dir_c4f_s6 --guia c4 --semilla 6
```

Si se corta, relanzar el puente y continuar desde el último punto de control
(`--generaciones` es el total):

```bash
python3 evolucionar.py --etiqueta dir_c4f_s6 --guia c4 --reanudar
```

Con otra etiqueta y `--semilla` se obtienen las demás semillas
(`dir_c4f_s7`, `dir_c4f_s8`, ...). NEAT-Python es reproducible con la
semilla, pero el simulador no: dos evoluciones con la misma semilla no dan la
misma población.

## Ejecutar y evaluar el controlador final

Con el guía en la configuración indicada (`c1`, `c2`, `c3` o `c4`):

```bash
python3 evaluar.py --genoma evoluciones/dir_c4f_s6/genomas/mejor_gen024.pkl --config c1 --episodios 3 --carpeta p2_eval/semilla6_c4f_id437
python3 evaluar.py --metricas --carpeta p2_eval/semilla6_c4f_id437
```

La evaluación de C4 está en `p2_eval/c4/c4f_s6_id437/`.

## Figuras

```bash
python3 curvas_p2.py --etiquetas dir_c4f_s6 --salida figuras/evolucion_c4f.png
python3 red_p2.py --genoma evoluciones/dir_c4f_s6/genomas/mejor_gen024.pkl --salida figuras/red_437.png
```
