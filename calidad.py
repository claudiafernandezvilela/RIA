#!/usr/bin/env python3
"""
Práctica 2 — Función de calidad (fitness) de cada individuo.

Se calcula al terminar el episodio a partir del registro de pasos: la lista
de diccionarios `info` que devuelve RoboboSeguirEnv.step(), uno por paso.
La red no recibe nunca la calidad; sólo sirve para comparar individuos, así
que puede usar información privilegiada del simulador (apartado 5).

Formulación mixta (ver calidad_p2.md). Por cada paso vivo

    r_t = K_VIVO + K_SEP * q_sep + K_X * q_x

y al final

    Q = 100 * sum(r_t) / N - P_CHOQUE * [choque]           en [-10, 100]

N es el número MÁXIMO de pasos del episodio, no los pasos vividos: un
episodio que se corta pronto suma menos (penalización implícita) y la
calidad es comparable aunque N cambie entre etapas de la evolución.

Uso desde el bucle de evaluación:

    from calidad import calidad
    registro = []                       # un info por paso
    ...
    genoma.fitness = calidad(registro, n_max=PASOS_EVAL)

Comprobación sin simulador (episodios inventados):

    python3 calidad.py
"""

import math

K_VIVO = 0.2           # por paso vivo: gradiente desde la generación 0
K_SEP = 0.6            # separación: término principal
K_X = 0.2              # centrado de la pelota en la imagen
SEP_BANDA_M = (0.25, 0.45)  # q_sep = 1 dentro de la banda (objetivo 0,35 m)
SEP_CHOQUE_M = 0.12         # q_sep = 0: colisión
SEP_LEJOS_M = 0.70          # q_sep = 0: demasiado lejos
X_CENTRO = 0.2              # q_x = 1 si |x| <= 0,2
P_CHOQUE = 10.0        # se resta al final si el episodio acaba en choque
# El guía no arranca hasta que el seguidor se le acerca: si a los 10 s la
# pelota no se ha desplazado 0,10 m, el episodio se da por fallido ahí
# (si no, quedarse quieto mirando la pelota a 0,62 m daba Q ≈ 44)
PASOS_ARRANQUE = 25
ARRANQUE_M = 0.10
# Término de parada (segunda formulación, opción calidad_parada del
# entorno.json): mientras el guía está parado, la puntuación del paso se
# multiplica por q_parada = 1 - v / V_PARADA_MS (0 por encima), con v la
# velocidad ordenada al seguidor. Sin él, la evolución en C4 aprovechaba las
# paradas para acercarse al guía en vez de detenerse.
V_PARADA_MS = 0.05     # q_parada = 0 a partir de esta velocidad
GUIA_QUIETO_MM = 4.0   # desplazamiento de la pelota por paso (~0,4 s):
                       # 0,01 m/s, el umbral de parada del anexo B.1
PASOS_QUIETO = 2       # pasos seguidos (~0,8 s > 0,5 s del anexo B.1)
# Además, se resta P_PARADA por cada parada del guía terminada (el guía
# vuelve a arrancar) en la que el seguidor no ha llegado a estar quieto
# (v < V_QUIETO_MS durante PASOS_QUIETO pasos seguidos): la parada no
# superada del anexo B.4, igual que P_CHOQUE con el choque.
P_PARADA = 3.0
V_QUIETO_MS = 0.01


def _q_sep(sep, banda=SEP_BANDA_M):
    """1 dentro de la banda; baja en línea recta hasta 0 en la colisión y
    a 0,70 m. Fuera de la banda siempre hay pendiente hacia ella."""
    cerca, lejos = banda
    if sep < cerca:
        return max(0.0, (sep - SEP_CHOQUE_M) / (cerca - SEP_CHOQUE_M))
    if sep > lejos:
        return max(0.0, (SEP_LEJOS_M - sep) / (SEP_LEJOS_M - lejos))
    return 1.0


def _q_x(x):
    """1 con la pelota en el centro de la imagen (|x| <= 0,2); 0 en el borde."""
    return min(1.0, max(0.0, (1.0 - abs(x)) / (1.0 - X_CENTRO)))


def sin_arranque(registro):
    """Número de pasos tras el que se corta el episodio porque el guía no ha
    arrancado (None si arrancó, si aún no han pasado 10 s o si no hay pose
    del guía, p. ej. en el robot real)."""
    if len(registro) < PASOS_ARRANQUE:
        return None
    inicio = registro[0].get('pelota_sim')
    ahora = registro[PASOS_ARRANQUE - 1].get('pelota_sim')
    if inicio is None or ahora is None:
        return None
    movido = math.hypot(ahora[0] - inicio[0], ahora[1] - inicio[1]) / 1000.0
    return PASOS_ARRANQUE if movido < ARRANQUE_M else None


def guia_parado(registro):
    """Lista de bool, uno por paso: el guía está parado (la pelota no se ha
    desplazado más de GUIA_QUIETO_MM en los últimos PASOS_QUIETO pasos). La
    espera inicial, antes de que el guía se mueva por primera vez, no es una
    parada: el guía no arranca hasta que el seguidor se acerca."""
    parado, quietos, arrancado, prev = [], 0, False, None
    for info in registro:
        p = info.get('pelota_sim')
        if p is None or prev is None:
            quietos = 0
        elif math.hypot(p[0] - prev[0], p[1] - prev[1]) < GUIA_QUIETO_MM:
            quietos += 1
        else:
            quietos, arrancado = 0, True
        prev = p
        parado.append(arrancado and quietos >= PASOS_QUIETO)
    return parado


def paradas_no_superadas(registro, parado):
    """Número de paradas del guía terminadas en el registro (tramos de
    `parado` seguidos de un paso con el guía en marcha) en las que el
    seguidor no estuvo quieto PASOS_QUIETO pasos seguidos."""
    n, en_parada, detenido, quietos = 0, False, False, 0
    for info, guia_quieto in zip(registro, parado):
        if guia_quieto:
            en_parada = True
            quietos = quietos + 1 if abs(info.get('v', 0.0)) < V_QUIETO_MS \
                else 0
            detenido = detenido or quietos >= PASOS_QUIETO
        elif en_parada:
            n += not detenido
            en_parada, detenido, quietos = False, False, 0
    return n


def calidad(registro, n_max, banda=None, parada=False, penalizacion=True):
    """Calidad del episodio a partir de los info de cada paso.

    Un paso cuenta como vivo si en él no se ha producido ningún fallo
    (choque, perdido o atascado): el paso del fallo ya no suma.

    `banda` (cerca, lejos) en metros sustituye a SEP_BANDA_M. Lo usa la
    evolución de C4 desde cero (calidad_banda_m en su entorno.json): con
    0,30-0,45 m el seguidor no puntúa al máximo pegado a 0,25 m, donde la
    pelota empieza a salirse de la imagen por abajo (unos 0,23 m).

    `parada` activa el término de parada (calidad_parada en entorno.json).
    `penalizacion` = False quita la resta de P_PARADA por parada no
    superada y deja solo el factor (calidad_penalizacion en entorno.json).
    """
    banda = tuple(banda) if banda is not None else SEP_BANDA_M
    corte = sin_arranque(registro)
    if corte is not None:
        registro = registro[:corte]
    parado = guia_parado(registro) if parada else [False] * len(registro)
    suma = 0.0
    for info, guia_quieto in zip(registro, parado):
        if info.get('choque') or info.get('perdido') or info.get('atascado'):
            continue

        sep = info.get('separacion')
        if sep is None or not math.isfinite(sep):
            raise ValueError(
                'El paso no tiene separación real. ¿Está el puente lanzado '
                "con modules:=\"['blob','sim']\" y se lee la pose del guía?")

        q_sep = _q_sep(sep, banda)
        q_x = _q_x(float(info['x'])) if info.get('visible') else 0.0

        r = K_VIVO + K_SEP * q_sep + K_X * q_x
        if guia_quieto:
            r *= max(0.0, 1.0 - abs(info.get('v', 0.0)) / V_PARADA_MS)
        suma += r

    q = 100.0 * suma / n_max
    if parada and penalizacion:
        q -= P_PARADA * paradas_no_superadas(registro, parado)

    # Choque con el guía, atasco contra el entorno o guía sin arrancar
    if corte is not None or (registro and (registro[-1].get('choque')
                                           or registro[-1].get('atascado'))):
        q -= P_CHOQUE
    return float(q)


def _paso(sep, x=0.0, visible=True, choque=False, perdido=False,
          atascado=False, pelota=None):
    """Un info con las claves que usa la calidad, como el de env.step().
    Sin `pelota`, el guía avanza 0,05 m por paso."""
    _paso.k = getattr(_paso, 'k', 0) + 1
    return {'separacion': sep, 'x': x, 'visible': visible, 'choque': choque,
            'perdido': perdido, 'atascado': atascado,
            'pelota_sim': pelota or (0.0, 50.0 * _paso.k)}


def _comprobar():
    """Episodios inventados de 125 pasos de 0,4 s (50 s, la duración de C2 y
    C3). La calidad debe ordenarlos de peor a mejor."""
    n = 125
    casos = {
        # Pierde al guía a los 4 s: se aleja y la pelota se sale de la imagen
        'aleatorio': [_paso(0.35 + 0.06 * k, x=0.6, visible=k < 5)
                      for k in range(9)]
                     + [_paso(0.91, visible=False, perdido=True)],
        # Aguanta 20 s dentro de la banda y lo pierde en una curva
        'regular': [_paso(0.45, x=0.2) for _ in range(49)]
                   + [_paso(0.95, visible=False, perdido=True)],
        # Sigue al guía todo el episodio, pero lejos (0,60 m)
        'lejos': [_paso(0.60, x=0.3) for _ in range(n)],
        # 0,35 m y centrado todo el episodio
        'bueno': [_paso(0.35, x=0.05) for _ in range(n)],
        # Como el bueno, pero no frena a tiempo y choca en el paso 115 (46 s)
        'choca': [_paso(0.35, x=0.05) for _ in range(114)]
                 + [_paso(0.10, choque=True)],
        # Se queda quieto girando a 0,62 m: el guía no arranca
        'quieto': [_paso(0.62, x=0.1, pelota=(0.0, 0.0)) for _ in range(n)],
    }
    print('{:10s} {:>8s}'.format('caso', 'calidad'))
    for nombre, reg in casos.items():
        print('{:10s} {:8.1f}'.format(nombre, calidad(reg, n)))


if __name__ == '__main__':
    _comprobar()
