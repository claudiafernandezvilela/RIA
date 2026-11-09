# Evoluciones finales de la P2

Aquí están solo las evoluciones del controlador final, una por semilla. El resto
de pruebas está en [`_descartadas/`](_descartadas/README.md).

| Semilla | Carpeta | Controlador | Estado |
|---|---|---|---|
| 2 | `inc_s2c_w40/` | id 1038 (`genomas/mejor_gen039.pkl`) | Terminada y evaluada: 9/9 episodios |
| Segunda semilla | pendiente | pendiente | Por hacer, con el mismo protocolo |

Resultados de la evaluación: [`../p2_eval/README.md`](../p2_eval/README.md).

## Protocolo de la semilla 2

Evolución incremental. Una sola calidad (`calidad.py`) en toda la cadena y
1 episodio por individuo.

| Generaciones | Guía | Pasos máx. | `v_max` | `w_max` |
|---|---|---|---|---|
| 0-9 | C1 (Crucero 10-10) | 245 | 0,20 | 0,8 |
| 10-19 | C2 (Crucero 10-40) | 175 | 0,30 | 0,4 |
| 20-29 | C2 (Crucero 10-40) | 300 | 0,30 | 0,4 |
| 30-39 | C3 (Variable 10-40) | 300 | 0,30 | 0,4 |

- Las generaciones 0-9 vienen de `_descartadas/inc_s2c`. El punto de control
  `chk/p2-10` es idéntico al de esa evolución.
- `entorno.json` guarda la configuración usada desde la generación 10.
- El último punto de control de la evolución es `chk/p2-40`.
- El episodio se alargó a 300 pasos porque con 175 (unos 67 s) la evolución no
  llegaba a la salida de la tercera curva.
- `w_max` se redujo a 0,4 porque la red giraba mucho más que las políticas SAC
  de la P1 y perdía la pelota de lado.

## Contenido de cada carpeta

| Fichero | Contenido |
|---|---|
| `config-p2.ini` | Configuración de NEAT, con la semilla |
| `entorno.json` | Configuración del entorno |
| `evolucion.csv` | Una fila por generación |
| `genomas/mejor_genNNN.pkl` | Mejor genoma de cada generación |
| `chk/p2-N` | Punto de control: población antes de la generación N |

`--guia` solo anota el CSV. El guía se cambia a mano en RoboboSim.
