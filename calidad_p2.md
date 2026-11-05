# Práctica 2 · Función de calidad

## Fórmula

Por cada paso vivo t (sin choque, pérdida del guía ni atasco):

```
r_t = 0,2  +  0,6 · q_sep  +  0,2 · q_x

q_sep = 1                          si 0,25 ≤ sep_t ≤ 0,45 m
        (sep_t − 0,12) / 0,13      si sep_t < 0,25 m   (0 en la colisión)
        max(0, (0,70 − sep_t) / 0,25)   si sep_t > 0,45 m

q_x   = min(1, (1 − |x_t|) / 0,8)   si se ve la pelota;   0 si no
```

Un controlador que mantiene la separación en la banda y la pelota centrada
(|x| ≤ 0,2) obtiene r_t = 1 en cada paso, así que llega a Q = 100.

Al final del episodio:

```
Q = 100 · (Σ_t r_t) / N  −  10 · [choque o guía sin arrancar]    Q ∈ [−10, 100]
```

N es el número máximo de pasos del episodio.

## Magnitudes

| Magnitud | Qué es | De dónde sale |
|---|---|---|
| `sep_t` | Separación entre el centro del seguidor y la pelota verde, en m | Simulador (privilegiada): pose del seguidor y pose del guía, con la pelota 0,08 m detrás de él |
| `x_t` | Posición horizontal de la pelota en la imagen, en [−1, 1]: 0 en el centro, ±1 en los bordes | Cámara del seguidor (blob verde), por ROS 2 |
| `visible_t` | 1 si la cámara ve la pelota, 0 si no | Cámara del seguidor (blob verde), por ROS 2 |
| `fallo_t` | 1 si en el paso t hay colisión, guía perdido o atasco | Fin de episodio del entorno (simulador) |
| `d_guía` | Desplazamiento de la pelota del guía desde el inicio, en m | Simulador (privilegiada): pose del guía |

## Términos

| Término | Coeficiente | Magnitud |
|---|---|---|
| Supervivencia | 0,2 por paso vivo | `fallo_t` (cuenta los pasos con `fallo_t` = 0) |
| Separación | 0,6 · q_sep por paso | `sep_t`. Máximo entre 0,25 y 0,45 m (objetivo 0,35 m); 0 a 0,12 m y desde 0,70 m |
| Centrado | 0,2 · q_x por paso | `x_t` y `visible_t`. Máximo con \|x\| ≤ 0,2 |
| Choque | −10 al final | `fallo_t` en el último paso, si fue colisión o atasco; o `d_guía` < 0,10 m a los 10 s |

## Duración de la evaluación

Pasos de unos 0,37–0,4 s. Duración máxima elegida para incluir las curvas
(en C1, 175 pasos acababan antes de terminar la curva):

| Configuración | Duración | N |
|---|---|---|
| C2, C3 | 50 s | 125 |
| C4 | 60 s | 150 |
| C1 | 90 s | 245 |

## Cuándo se corta

- Colisión: separación < 0,12 m.
- Guía perdido: separación > 0,90 m, o 7 pasos (unos 3 s) sin ver la pelota.
- Atasco: 5 pasos ordenando avanzar sin desplazarse 20 mm.
- Guía sin arrancar: a los 10 s (25 pasos) la pelota se ha desplazado menos
  de 0,10 m. El guía sólo arranca cuando el seguidor se le acerca; sin este
  corte, quedarse quieto girando para ver la pelota a 0,62 m daba Q ≈ 44.

## Cómo se acumula

Mixta: un término en cada paso vivo más una penalización según el desenlace (choque, atasco o guía sin arrancar).
