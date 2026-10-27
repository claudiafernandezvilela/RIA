# Práctica 2 · Función de calidad

Propuesta para la revisión de la semana 1. Se comparan dos formulaciones (A y B),
como pide el apartado 5 del enunciado. La red no recibe nunca la calidad: sólo sirve
para ordenar a los individuos, así que puede usar información privilegiada del
simulador.

## 1. Magnitudes que se usan

Todas salen de `info` en cada `step()` del entorno de la P1 (`env.py`).

| Símbolo | Magnitud | De dónde sale | ¿Está en la observación de la red? |
|---|---|---|---|
| `sep_t` | Separación real seguidor–pelota, en m | Simulador: pose del seguidor (`sim/robot_location`) y pose del guía (`robobosim`), pelota 0,08 m detrás del guía (anexo B.1) | No (privilegiada). La red la infiere del tamaño del blob y de Δs |
| `desv_t` | Desviación entre el rumbo del seguidor y la dirección a la pelota, en grados | Simulador, mismas poses | No (privilegiada). La red ve su equivalente, la x del blob |
| `vivo_t` | 1 si en el paso t el episodio sigue en marcha | Fin de episodio del entorno | — |
| `choque` | El episodio terminó por colisión con el guía (`sep < 0,12 m`) o por atasco contra el entorno | Fin de episodio del entorno | — |

La observación de la red no cambia respecto a la P1 (C2/C3): visible, x del blob,
tamaño del blob, v y w del paso anterior y Δs (6 entradas). La acción sí cambia:
la velocidad lineal pasa de `[0,01, 0,20]` a `[0, 0,20]` m/s para que el seguidor
pueda detenerse en las paradas del guía (C4).

## 2. Duración y fin de cada episodio de evaluación

- **Paso:** 0,2 s (`paso_s`).
- **Duración máxima:** `N = 150` pasos (30 s) en C1–C3 y `N = 200` pasos (40 s)
  en C4, para que haya al menos una curva y, en C4, alguna parada. La calidad se
  divide por `N`, así que es comparable aunque la duración cambie entre etapas de
  la evolución incremental.
- **Episodios por individuo:** 1 (`k = 1`). Antes de elegir el controlador final, se
  vuelven a evaluar los 5 mejores con varios episodios.
- **Estado inicial:** reinicio de la simulación; los dos robots en la posición del
  escenario, el seguidor parado.
- **Cortes antes de tiempo** (los mismos del anexo B.3, para que la calidad y el
  protocolo midan el mismo fallo):

| Fallo | Condición |
|---|---|
| Colisión | `sep < 0,12 m` |
| Guía perdido | `sep > 0,90 m`, o pelota sin detectar 3 s seguidos (15 pasos) |
| Atasco | 5 pasos ordenando avanzar (`v ≥ 0,03 m/s`) y moviéndose menos de 20 mm (choque con el entorno). Cuenta como "otra causa" en el protocolo |
| Tiempo agotado | `N` pasos: episodio completado, no es fallo |

## 3. Formulación A · Mixta (seguimiento centrado y penalización por choque)

Por cada paso vivido se suma un término. Al acabar el episodio se resta una
penalización si terminó por choque.

```
r_t = 0,2 · 1  +  0,6 · q_sep(sep_t)  +  0,2 · q_desv(desv_t)          ∈ [0, 1]

q_sep  = max(0, 1 − |sep_t − 0,35| / 0,15)      → 1 a 0,35 m; 0 a 0,20 m y a 0,50 m
q_desv = max(0, 1 − |desv_t| / 45°)             → 1 mirando a la pelota; 0 a 45°

Q_A = 100 · (1/N) · Σ_t r_t  −  10 · [choque]                           ∈ [−10, 100]
```

| Término | Coef. | Magnitud | Por qué está |
|---|---|---|---|
| Supervivencia | 0,2 por paso | `vivo_t` | Da **gradiente desde la generación 0**: entre dos individuos que pierden al guía lejos de la banda, puntúa más el que aguanta más pasos (el que lo pierde en el segundo 8 frente al del segundo 2) |
| Separación | 0,6 por paso | `sep_t` | Es el objetivo principal. El triángulo tiene su máximo en 0,35 m (dentro de la banda 0,20–0,45 m y donde la pelota se ve entera con tilt 100, según la P1) y no tiene meseta, así que **no compensa quedarse en el borde** de la banda |
| Orientación | 0,2 por paso | `desv_t` | Que el seguidor mire hacia el guía: mantiene la pelota en imagen y evita derrapes laterales y salidas de carril |
| Choque | −10 al final | `choque` | El fallo por perder al guía ya se castiga implícitamente: los pasos no vividos no suman. El choque se castiga además porque es un fallo de seguridad y porque, en C4, un individuo que no frena llegaría al choque con la calidad acumulada hasta ahí. 10 equivale a 10 % del máximo |

**Tipo:** mixta (incremental + penalización por el desenlace).

## 4. Formulación B · Incremental (porcentaje en banda)

Es la formulación de comparación: más simple y calcada de la métrica del anexo B.4
("porcentaje de pasos dentro de la banda").

```
r_t = 0,5 · 1  +  0,5 · [0,20 ≤ sep_t ≤ 0,45]                          ∈ {0,5, 1}

Q_B = 100 · (1/N) · Σ_t r_t                                            ∈ [0, 100]
```

| Término | Coef. | Magnitud | Por qué está |
|---|---|---|---|
| Supervivencia | 0,5 por paso | `vivo_t` | Gradiente desde la generación 0 |
| En banda | 0,5 por paso | `sep_t` | Premia directamente lo que mide el protocolo |

**Tipo:** incremental, sin término final.

## 5. Qué se espera de la comparación

| | A | B |
|---|---|---|
| Separación | Tiende a 0,35 m (máximo del triángulo) | Cualquier punto de la banda vale igual: es probable que se quede en el borde lejano, a 0,45 m, que es el más seguro frente al choque |
| Orientación | Premiada | No interviene: puede zigzaguear sin perder puntos |
| Paradas (C4) | Chocar resta 10 | Chocar sólo corta el episodio; si la parada llega tarde, apenas se pierde nada |
| Atajos posibles | Girar sobre sí mismo: no sirve, porque la separación crece y el episodio se corta. Pararse: el guía se aleja y se corta a 0,90 m | Los mismos, más "quedarse en el borde de la banda" |

Lo que salga se compara con las curvas de evolución, las métricas del anexo B y los
vídeos (salirse del carril sólo se ve en los vídeos).

## 6. Referencias antes de evolucionar

- Calidad del **controlador programado a mano** del reto y de la **política SAC de la
  P1**, evaluados con A y con B: dan una línea horizontal de referencia en las curvas
  y permiten comprobar que la calidad ordena bien comportamientos conocidos.
- Calidad de la **población inicial** (redes aleatorias): es la línea base.

## 7. Qué parte se podría calcular a bordo

`desv_t` tiene un equivalente a bordo: la x del blob. `sep_t` sólo se puede estimar a
partir del tamaño del blob, que no es monótono con la distancia (P1). Los cortes por
choque o por guía perdido dependen de la separación real. Por eso esta calidad sólo
existe en simulación y no permite evolucionar directamente en el robot real
(evolución *embodied*).
