# Práctica 1 · Seguimiento de un vehículo en la ciudad de Robobo

Aprendizaje por refuerzo (SAC, Stable-Baselines3) para que un Robobo siga al
vehículo guía de "Follow City" en RoboboSim.

## Archivos

| Archivo | Qué es |
|---|---|
| `env.py` | Entorno Gymnasium `RoboboSeguirEnv` (observación, acción, recompensa, fin de episodio, reinicio) |
| `train.py` | Entrenamiento (`--entrenar`), línea base (`--aleatorio`), comprobación (`--comprobar`), calibración (`--calibrar`) |
| `evaluar.py` | Evaluador con el protocolo del anexo B y tablas de métricas (`--metricas`) |
| `config.json` | Configuración base. **Es la de C1** |
| `config_c3.json` | Valores propios de **C3**, aplicados encima de `config.json` |
| `p1_modelo_<alg>_<etiqueta>.zip` | Modelo entrenado |
| `p1_modelo_<alg>_<etiqueta>.json` | Copia de la configuración completa con la que se entrenó ese modelo; `evaluar.py` la usa |
| `p1_logs/monitor_<alg>_<etiqueta>.monitor.csv` | Registro por episodio del entrenamiento (curvas de aprendizaje) |
| `p1_eval/episodios.csv` | Una fila por episodio evaluado (desenlace) |
| `p1_eval/<modelo>_<config>_ep<n>.csv` | Registro por paso de cada episodio evaluado |
| `p1_eval/metricas.md` | Tablas del anexo B.4 (`python3 evaluar.py --metricas`) |

## Puente ROS 2

```bash
ros2 run robobo_ros2 robobo_container --ros-args -p ip:=host.docker.internal -p modules:="['blob','sim']"
```

Sin el módulo `sim` no llegan las posiciones del simulador: no hay separación
real, ni detección de atasco, y el fin de episodio se aproxima con el tamaño
del blob (los avisos `[aviso] No aparece .../robot_location` lo indican).

## C1 · Crucero 10-10

- **Configuración:** `config.json` (sin `--config-json`).
- Observación de 5 valores (blob visible, x, tamaño, acción anterior).
  Recompensa de distancia con el tamaño del blob (`s_objetivo` 0,50,
  `s_tolerancia` 0,10).
- **Modelos:** `p1_modelo_sac_c1_s1`, `_s2`, `_s3` (semillas 1, 2, 3).
  **Final: `c1_s1`.**

```bash
python3 train.py --entrenar --algoritmo sac --pasos 10000 --semilla 1 --etiqueta c1_s1
python3 evaluar.py --config c1 --algoritmo sac --etiqueta c1_s1
```

## C3 · Variable 10-40

- **Configuración:** `config.json` + `config_c3.json`:
  - `obs_delta`: la observación añade Δs (variación del tamaño del blob) → 6 valores.
  - `dist_por_separacion`: el término de distancia usa la separación real del
    simulador, objetivo 0,35 m, tolerancia 0,08 m por el lado cercano y 0,12 m
    por el lejano (sólo en entrenamiento; la observación no cambia).
  - `tilt_angulo` 100 (cámara más baja) y `s_max` 450.
- **Modelos:** `p1_modelo_sac_c3_tilt100_s1` (y `_s2`, `_s3` si se entrenan).
  **Final: `c3_tilt100_s1`.**

```bash
python3 train.py --entrenar --algoritmo sac --pasos 20000 --pasos-max 300 --semilla 1 --etiqueta c3_tilt100_s1 --config-json config_c3.json
python3 evaluar.py --config c3 --algoritmo sac --etiqueta c3_tilt100_s1
```

### Experimentos intermedios de C3

La configuración exacta de cada uno está en su `p1_modelo_sac_<etiqueta>.json`.

| Etiqueta | Cambio respecto al anterior | Resultado en evaluación |
|---|---|---|
| `c3_s1` | igual que C1 | completa; 7,9 % en banda, 0,61 m |
| `c3_tol30_s1` | `s_tolerancia` 0,30 | completa; 17,1 % en banda, 0,51 m |
| `c3_delta_s1` | + Δs en la observación; 15 000 pasos, `--pasos-max 300` | 1 de 3 completados; 22,7 % en banda, 0,50 m |
| `c3_sep_s1` | distancia por separación real, objetivo 0,30 m | pierde al guía (pelota fuera de imagen < 0,25 m); 59 % en banda |
| `c3_sep35_s1` | objetivo 0,35 m, tolerancia asimétrica; 20 000 pasos | pierde al guía igual; 73 % en banda |
| `c3_tilt100_s1` | tilt 100, `s_max` 450 | **2 de 4 completados; 72 % en banda, 0,40 m** |

Notas sobre `p1_eval/`:
- `c3_sep35_s1` episodios 2 y 3 son las pruebas de tilt 80 y 100 (no son
  evaluaciones de ese modelo).
- Las dos primeras filas de `c1_s1` en `episodios.csv` no tienen su CSV de
  pasos (se sobrescribió; ya corregido en `evaluar.py`).
- `c3_s2` (entrenado con la configuración de C1) no tiene CSV de pasos.

## Métricas

```bash
python3 evaluar.py --metricas
```
