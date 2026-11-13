#!/usr/bin/env python3
"""
Práctica 2 — Reevaluación de los mejores genomas de una evolución.

La calidad de un solo episodio es muy ruidosa, así que el mejor genoma de
cada generación se vuelve a evaluar varios episodios y se resume qué hace:
calidad media, separación, tiempo en la banda, visibilidad, velocidad y
cuánto se han desplazado el seguidor y la pelota del guía.

Uso (RoboboSim y el puente como en evolucionar.py):

    python3 reevaluar.py --etiqueta c2_s1 --episodios 5 --n 6

Escribe evoluciones/<etiqueta>/reevaluacion.csv (una fila por episodio).
"""

import argparse
import csv
import glob
import math
import os
import pickle
import statistics

import neat

from calidad import calidad
from env import RoboboSeguirEnv, cargar_config
from evolucionar import RUTA_EVOLUCIONES, desenlace, evaluar_genoma

BANDA_M = (0.25, 0.45)


def recorrido(puntos):
    """Distancia recorrida en m por una lista de posiciones (x, z) en mm."""
    puntos = [p for p in puntos if p is not None]
    return sum(math.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(puntos, puntos[1:])) / 1000.0


def resumen(registro, n_max, cfg):
    seps = [i['separacion'] for i in registro if i.get('separacion') is not None]
    vis = [i for i in registro if i.get('visible')]
    return {
        'calidad': round(calidad(registro, n_max, cfg), 2),
        'pasos': len(registro),
        'desenlace': desenlace(registro),
        'sep_ini': round(seps[0], 3),
        'sep_med': round(statistics.median(seps), 3),
        'sep_fin': round(seps[-1], 3),
        'en_banda': round(sum(BANDA_M[0] <= s <= BANDA_M[1] for s in seps)
                          / len(seps), 3),
        'visible': round(len(vis) / len(registro), 3),
        'x_abs': round(statistics.mean(abs(i['x']) for i in vis), 3) if vis else '',
        'v_media': round(statistics.mean(i['v'] for i in registro), 3),
        'rec_robot_m': round(recorrido([i['pose_sim'][:2] if i.get('pose_sim')
                                        else None for i in registro]), 2),
        'rec_pelota_m': round(recorrido([i.get('pelota_sim')
                                         for i in registro]), 2),
    }


def main():
    p = argparse.ArgumentParser(
        description='Reevalúa los mejores genomas de una evolución.')
    p.add_argument('--etiqueta', required=True)
    p.add_argument('--episodios', type=int, default=5)
    p.add_argument('--n', type=int, default=6,
                   help='genomas distintos a reevaluar (los de mayor calidad '
                        'registrada)')
    p.add_argument('--pasos-max', type=int, default=125)
    args = p.parse_args()

    carpeta = os.path.join(RUTA_EVOLUCIONES, args.etiqueta)
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         os.path.join(carpeta, 'config-p2.ini'))

    # Un genoma por id (el mismo élite aparece en varias generaciones)
    genomas = {}
    for ruta in sorted(glob.glob(os.path.join(carpeta, 'genomas', 'mejor_gen*.pkl'))):
        with open(ruta, 'rb') as f:
            g = pickle.load(f)
        gen = int(os.path.basename(ruta)[9:12])
        if g.key not in genomas or g.fitness > genomas[g.key][1].fitness:
            genomas[g.key] = (gen, g)
    elegidos = sorted(genomas.values(), key=lambda t: -t[1].fitness)[:args.n]

    cfg = cargar_config(os.path.join(carpeta, 'entorno.json'))
    env = RoboboSeguirEnv(pasos_max=args.pasos_max, usar_simulador=True,
                          config=cfg)
    ruta_csv = os.path.join(carpeta, 'reevaluacion.csv')
    filas = []
    try:
        for gen, g in elegidos:
            red = neat.nn.FeedForwardNetwork.create(g, config)
            print('\nid {} (generación {}, calidad en la evolución {:.1f})'
                  .format(g.key, gen, g.fitness))
            for ep in range(1, args.episodios + 1):
                r = resumen(evaluar_genoma(env, red, args.pasos_max),
                            args.pasos_max, cfg)
                filas.append(dict(id=g.key, generacion=gen, episodio=ep, **r))
                print('  ep {}  calidad {:5.1f}  pasos {:3d} {:9s} sep '
                      '{:.2f}/{:.2f}/{:.2f}  banda {:3.0f}%  visible {:3.0f}%  '
                      'v {:.3f}  robot {:5.2f} m  pelota {:5.2f} m'.format(
                          ep, r['calidad'], r['pasos'], r['desenlace'],
                          r['sep_ini'], r['sep_med'], r['sep_fin'],
                          100 * r['en_banda'], 100 * r['visible'],
                          r['v_media'], r['rec_robot_m'], r['rec_pelota_m']),
                      flush=True)
            cal = [f['calidad'] for f in filas if f['id'] == g.key]
            print('  media {:.1f} ± {:.1f}'.format(
                statistics.mean(cal), statistics.pstdev(cal)))
    except (RuntimeError, KeyboardInterrupt) as e:
        print('\nReevaluación detenida: {}'.format(e or 'Ctrl-C'))
    finally:
        env.close()
        if filas:
            with open(ruta_csv, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(filas[0]))
                w.writeheader()
                w.writerows(filas)
            print('\nGuardado ' + ruta_csv)


if __name__ == '__main__':
    main()
