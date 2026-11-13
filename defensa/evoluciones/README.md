# Evoluciones de la P2

Aquí están las evoluciones de los controladores (una por semilla) y las de C4.
El controlador final es el **id 437** de `final_s6`.
El resto de pruebas está en [`_descartadas/`](_descartadas/README.md).

| Semilla | Carpeta | Controlador | Estado |
|---|---|---|---|
| 6 | `final_s6/` | **id 437** (`controlador_final_s6_id437.pkl`, copia de `genomas/mejor_gen024.pkl`), controlador final | Configuración final, evolucionada en C4. Terminada y evaluada: 12/12 episodios en C1-C4 |
| 7 | `dir_c4f_s7/` | id 276 (`genomas/mejor_gen024.pkl`), candidato | Configuración final. Generaciones 0-24; el 276 completa 3/3 en C1 y C2 (C3 y C4 pendientes) |
| 8 | `dir_c4f_s8/` | ninguno | Configuración final, segunda semilla. Generaciones 0-24 hechas; no aprendió (mejor 15, media 9 en la última) |
| 2 | `inc_s2c_w40/` | id 1038 (`genomas/mejor_gen039.pkl`) | Terminada y evaluada: 9/9 episodios en C1-C3, 0/2 en C4 |
| 3 | `inc_s3c/` | pendiente | Generaciones 0-39 hechas. El mejor final, id 971, completa 1/9 |

Resultados de la evaluación: [`../p2_eval/README.md`](../p2_eval/README.md).

## Protocolo de las semillas 2 y 3

Evolución incremental. Una sola calidad (`calidad.py`, banda 0,25-0,45 m) en
toda la cadena y 1 episodio por individuo.

| Generaciones | Guía | Pasos máx. | `v_max` | `w_max` |
|---|---|---|---|---|
| 0-9 | C1 (Crucero 10-10) | 245 | 0,20 | 0,8 |
| 10-19 | C2 (Crucero 10-40) | 175 | 0,30 | 0,4 |
| 20-29 | C2 (Crucero 10-40) | 300 | 0,30 | 0,4 |
| 30-39 | C3 (Variable 10-40) | 300 | 0,30 | 0,4 |

- `entorno.json` guarda la configuración usada desde la generación 10.
- El episodio se alargó a 300 pasos porque con 175 (unos 67 s) la evolución no
  llegaba a la salida de la tercera curva.
- `w_max` se redujo a 0,4 porque la red giraba mucho más que las políticas SAC
  de la P1 y perdía la pelota de lado.

Semilla 2:

- Las generaciones 0-9 vienen de `_descartadas/inc_s2c`. El punto de control
  `chk/p2-10` es idéntico al de esa evolución.
- El último punto de control de la evolución es `chk/p2-40`.

Semilla 3:

- Evolución completa en la misma carpeta, puntos de control `chk/p2-1` a
  `chk/p2-40`.
- Mejor de cada generación en la etapa C3: 798 (31), 803 (32-33), 876 (34),
  918 (35-36) y 971 (37-39). El 754 es el mejor de la generación 29, antes
  de C3.

## C4 (Variable 10-40 con paradas)

Paradas del guía configuradas en RoboboSim: `Stop times` 2-5 s y
`Stop chances` 60. Evaluaciones en [`../p2_eval/c4/`](../p2_eval/c4/README.md).

| Carpeta | Origen | Generaciones | Pasos | Población | Episodios por individuo | Banda de la calidad |
|---|---|---|---|---|---|---|
| `inc_s2c_w40_c4/` | Continuación de `inc_s2c_w40` desde `chk/p2-40` | 40-59 | 300 | 30 | 1 | 0,25-0,45 m |
| `dir_c4_s5/` | Desde cero, semilla 5 (`config_descartadas/config_c4_dir.json`) | 0-34 | 200 | 20 | 2 | 0,30-0,45 m |
| `dir_c4p_s6/` | Desde cero, semilla 6, con el término de parada y la penalización (`config_descartadas/config_c4_parada.json`) | 0-16, detenida: no aprende | 200 | 20 | 2 | 0,30-0,45 m |
| `dir_c4p_s7/` | Igual, semilla 7 | 0-24 | 200 | 20 | 2 | 0,30-0,45 m |
| `final_s6/` | Desde cero, semilla 6, configuración final (`config_c4_final.json`) | 0-24 | 200 | 20 | 2 | 0,30-0,45 m |
| `dir_c4f_s7/` | Igual, semilla 7 | 0-24 | 200 | 20 | 2 | 0,30-0,45 m |
| `dir_c4f_s8/` | Igual, semilla 8 | 0-24 | 200 | 20 | 2 | 0,30-0,45 m |
| `dir_c4f_s9/` | Igual, semilla 9 | en marcha (25 generaciones) | 200 | 20 | 2 | 0,30-0,45 m |

- `dir_c4_s5` usa una segunda formulación de la calidad: la banda en la que la
  separación puntúa al máximo empieza en 0,30 m, porque a unos 0,23 m la pelota
  se sale de la imagen por abajo.
- `dir_c4p_s6` usa una tercera formulación: además, con el guía parado la
  puntuación del paso se multiplica por 1 − |v|/0,05 (0 a partir de
  0,05 m/s) y se restan 3 puntos por cada parada en la que el seguidor no
  llega a estar quieto (v < 0,01 m/s durante 2 pasos). Con la calidad de
  `dir_c4_s5`, la evolución aprovechaba las paradas para acercarse al guía en
  lugar de detenerse. No aprendió: en la generación 16 la mejor calidad era
  15 (74 en la semilla 5) y los episodios duraban unos 22 pasos de media.
  Con v ≥ 0, la salida tanh nunca da v = 0 exacta, así que pararse era
  imposible y la penalización castigaba a todos por igual. Consola en
  `dir_c4p_s6/consola.log`. La semilla 7 (`dir_c4p_s7`) sí avanza, a un
  ritmo parecido al de la semilla 5 (calidad media 12-14 en las generaciones
  20-24, frente a 13-18), pero sus mejores (293 en la generación 15, 394 en
  la 21, 431 en la 23) bajan a 12-19 al reevaluarlos en la generación
  siguiente. Consola en `dir_c4p_s7/consola.log`.
- `final_s6` y `dir_c4f_s7` a `dir_c4f_s9` (configuración final) cambian tres cosas
  respecto a `dir_c4_s5`:
  - `v_min` = −0,05 m/s con `v_sin_marcha_atras`: la v negativa se recorta
    a 0, así que toda salida por debajo de −0,71 da v = 0. Existe una
    distancia de equilibrio a la que el seguidor se detiene sin saturar la
    tanh, y nunca retrocede.
  - `obs_memoria`: sin pelota en la imagen, la entrada de tamaño conserva el
    último valor visto en lugar de 0, que la red leía como "muy lejos" y
    aceleraba (fallo del 557 en C3 y del 474 en C4).
  - Término de parada de `dir_c4p_s6` sin la penalización
    (`calidad_penalizacion: false`): solo el factor 1 − |v|/0,05.
- `final_s6`:
  - Se llamaba `dir_c4f_s6`. Las consolas y los registros de evaluación
    del 310 y el 376 (`../p2_eval/c4/c4f_s6_id*`) conservan ese nombre.
  - Mejor de cada generación: 4-27 en las generaciones 0-9, 96-98 en las
    10-13 (id 193 en las 10-12), 57 en las 14-15 y 92-95 en las 16-24
    (310 en las 17-18, 376 en las 21-22, 437 en la 24). La media sube hasta
    58 en la 24.
  - Se interrumpió en la generación 14 y se reanudó desde `chk/p2-14`.
    `chk_descartado/p2-15` es el punto de control de un intento fallido de
    esa reanudación (el simulador no respondía bien); no se usa.
- RoboboSim tiene que estar en primer plano. Con el ordenador desatendido
  (ventana en segundo plano o pantalla apagada) el simulador se comporta
  distinto: el 376, el 437 y el 310 completaron 0/9 episodios en C4 evaluados
  así, y 8/9 con RoboboSim delante. Probablemente explica también los saltos
  de la calidad en `final_s6` y el fallo del 193 en C4
  (`../p2_eval/c4/prueba_id193`).
- Con 2 episodios por individuo, la calidad es la media de los dos
  (`episodios_individuo.txt` en la carpeta).

## Contenido de cada carpeta

| Fichero | Contenido |
|---|---|
| `config-p2.ini` | Configuración de NEAT, con la semilla |
| `entorno.json` | Configuración del entorno |
| `evolucion.csv` | Una fila por generación |
| `genomas/mejor_genNNN.pkl` | Mejor genoma de cada generación |
| `chk/p2-N` | Punto de control: población antes de la generación N |
| `episodios_individuo.txt` | Episodios por individuo, si no es 1 |
| `consola.log` | Salida de la consola durante la evolución (solo en las de C4 desde cero) |

`--guia` solo anota el CSV. El guía se cambia a mano en RoboboSim.
