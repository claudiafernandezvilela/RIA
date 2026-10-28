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
SEP_OBJETIVO_M = 0.35  # máximo del triángulo de separación
SEP_TOL_M = 0.15       # q_sep = 0 a 0,20 m y a 0,50 m
P_CHOQUE = 10.0        # se resta al final si el episodio acaba en choque


def calidad(registro, n_max):
    """Calidad del episodio a partir de los info de cada paso.

    Un paso cuenta como vivo si en él no se ha producido ningún fallo
    (choque, perdido o atascado): el paso del fallo ya no suma.
    """
    suma = 0.0
    for info in registro:
        if info.get('choque') or info.get('perdido') or info.get('atascado'):
            continue

        sep = info.get('separacion')
        if sep is None or not math.isfinite(sep):
            raise ValueError(
                'El paso no tiene separación real. ¿Está el puente lanzado '
                "con modules:=\"['blob','sim']\" y se lee la pose del guía?")

        q_sep = max(0.0, 1.0 - abs(sep - SEP_OBJETIVO_M) / SEP_TOL_M)

        q_x = (1.0 - min(abs(float(info['x'])), 1.0)
               if info.get('visible') else 0.0)

        suma += K_VIVO + K_SEP * q_sep + K_X * q_x

    q = 100.0 * suma / n_max

    # Choque con el guía o atasco contra el entorno: sólo en el último paso
    if registro and (registro[-1].get('choque') or registro[-1].get('atascado')):
        q -= P_CHOQUE
    return float(q)


def _paso(sep, x=0.0, visible=True, choque=False, perdido=False,
          atascado=False):
    """Un info con las claves que usa la calidad, como el de env.step()."""
    return {'separacion': sep, 'x': x, 'visible': visible, 'choque': choque,
            'perdido': perdido, 'atascado': atascado}


def _comprobar():
    """Episodios inventados de 125 pasos de 0,4 s (50 s, la duración de C2 y
    C3). La calidad debe ordenarlos de peor a mejor."""
    n = 125
    casos = {
        # Pierde al guía a los 4 s: se aleja y la pelota se sale de la imagen
        'aleatorio': [_paso(0.35 + 0.06 * k, x=0.6, visible=k < 5)
                      for k in range(9)]
                     + [_paso(0.91, visible=False, perdido=True)],
        # Aguanta 20 s en el borde lejano de la banda y lo pierde en una curva
        'regular': [_paso(0.45, x=0.2) for _ in range(49)]
                   + [_paso(0.95, visible=False, perdido=True)],
        # Borde de la banda todo el episodio, centrado
        'borde': [_paso(0.44, x=0.05) for _ in range(n)],
        # 0,35 m y centrado todo el episodio
        'bueno': [_paso(0.35, x=0.05) for _ in range(n)],
        # Como el bueno, pero no frena a tiempo y choca en el paso 115 (46 s)
        'choca': [_paso(0.35, x=0.05) for _ in range(114)]
                 + [_paso(0.10, choque=True)],
    }
    print('{:10s} {:>8s}'.format('caso', 'calidad'))
    for nombre, reg in casos.items():
        print('{:10s} {:8.1f}'.format(nombre, calidad(reg, n)))


if __name__ == '__main__':
    _comprobar()
