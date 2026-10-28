# Práctica 2 · Función de calidad

## Fórmula

Por cada paso vivo t (sin choque, pérdida del guía ni atasco):

```
r_t = 0,2  +  0,6 · q_sep  +  0,2 · q_x

q_sep = max(0, 1 − |sep_t − 0,35| / 0,15)
q_x   = 1 − |x_t|   si se ve la pelota;   0 si no
```

Al final del episodio:

```
Q = 100 · (Σ_t r_t) / N  −  10 · [choque]          Q ∈ [−10, 100]
```

N es el número máximo de pasos del episodio.

## Magnitudes

| Magnitud | Qué es | De dónde sale |
|---|---|---|
| `sep_t` | Separación entre el centro del seguidor y la pelota verde, en m | Simulador (privilegiada): pose del seguidor y pose del guía, con la pelota 0,08 m detrás de él |
| `x_t` | Posición horizontal de la pelota en la imagen, en [−1, 1]: 0 en el centro, ±1 en los bordes | Cámara del seguidor (blob verde), por ROS 2 |
| `visible_t` | 1 si la cámara ve la pelota, 0 si no | Cámara del seguidor (blob verde), por ROS 2 |
| `fallo_t` | 1 si en el paso t hay colisión, guía perdido o atasco | Fin de episodio del entorno (simulador) |

## Términos

| Término | Coeficiente | Magnitud |
|---|---|---|
| Supervivencia | 0,2 por paso vivo | `fallo_t` (cuenta los pasos con `fallo_t` = 0) |
| Separación | 0,6 · q_sep por paso | `sep_t`. Máximo a 0,35 m, 0 a 0,20 y 0,50 m |
| Centrado | 0,2 · q_x por paso | `x_t` y `visible_t` |
| Choque | −10 al final | `fallo_t` en el último paso, si fue colisión o atasco |

## Duración de la evaluación

Pasos de unos 0,4 s. Duración máxima elegida para incluir las curvas:

| Configuración | Duración | N |
|---|---|---|
| C2, C3 | 50 s | 125 |
| C4 | 60 s | 150 |
| C1 | 70 s | 175 |

## Cuándo se corta

- Colisión: separación < 0,12 m.
- Guía perdido: separación > 0,90 m, o 7 pasos (unos 3 s) sin ver la pelota.
- Atasco: 5 pasos ordenando avanzar sin desplazarse 20 mm.

## Cómo se acumula

Mixta: un término en cada paso vivo más una penalización según el desenlace (choque).
