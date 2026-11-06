#!/usr/bin/env python3
"""
Práctica 2 — Topología de la red de un genoma (figura e interpretación).

Dibuja la red por capas con Matplotlib (función dibujar_red de las
indicaciones técnicas, apartado 7): entradas a la izquierda, nodos ocultos
según su profundidad y salidas a la derecha. Sólo las conexiones activas;
el grosor es proporcional a |peso| y el color indica el signo (azul
positivo, rojo negativo), con el valor del peso junto a cada flecha.

Imprime además los sesgos de los nodos y la lista de conexiones activas,
que es lo que se interpreta en la memoria (qué hace con cada entrada y qué
conexiones llevan la información de la pelota a cada actuador).

Las activaciones de NEAT-Python están escaladas: cada nodo calcula
tanh(2,5·(sesgo + Σ peso·entrada)).

Uso:
  python3 red_p2.py --genoma evoluciones/c1_s2/genomas/mejor_gen020.pkl \\
                    --salida figuras/red_c1.png
"""

import argparse
import json
import os
import pickle

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import neat

# Mismo orden que RoboboSeguirEnv._observacion y la acción del entorno
ENTRADAS = ['visible', 'x (blob)', 'tamaño (blob)', 'v anterior',
            'w anterior', 'Δ tamaño']
SALIDAS = ['v (avance)', 'w (giro)']

ACENTO = '#2a6fdb'
NEGATIVO = '#d93025'
TINTA = '#202124'
TINTA_2 = '#5f6368'


def capas_de(genoma, config):
    """Nodos por capas: entradas, ocultos por profundidad (camino más largo
    desde las entradas) y salidas. Devuelve (capas, conexiones activas)."""
    gc = config.genome_config
    entradas, salidas = list(gc.input_keys), list(gc.output_keys)
    activas = [c.key for c in genoma.connections.values() if c.enabled]
    prof = {n: 0 for n in entradas}
    for _ in range(len(genoma.nodes) + 1):
        for (a, b) in activas:
            nueva = prof[a] + 1 if a in prof and a != b else -1
            if prof.get(b, -1) < nueva <= len(genoma.nodes):
                prof[b] = nueva
    ocultas = [n for n in prof if n not in entradas and n not in salidas]
    capas = [entradas]
    for p in sorted({prof[n] for n in ocultas}):
        capas.append(sorted(n for n in ocultas if prof[n] == p))
    capas.append(salidas)
    return capas, activas


def dibujar_red(genoma, config, nombres_entrada, nombres_salida, ruta,
                ancho_cm=16.0, alto_cm=9.0):
    capas, activas = capas_de(genoma, config)
    # Entradas y salidas centradas; los ocultos, en la parte de abajo y en
    # zigzag, para que las conexiones directas entrada -> salida no pasen
    # por encima de ellos
    pos = {n: (0, -(j - (len(capas[0]) - 1) / 2))
           for j, n in enumerate(capas[0])}
    pos.update({n: (len(capas) - 1, -1.6 * (j - (len(capas[-1]) - 1) / 2))
                for j, n in enumerate(capas[-1])})
    bajo = -(len(capas[0]) - 1) / 2
    for i, c in enumerate(capas[1:-1], 1):
        for j, n in enumerate(c):
            pos[n] = (i, bajo + 0.2 + 0.6 * (i % 2) + 1.0 * j)
    nombres = dict(zip(capas[0], nombres_entrada))
    nombres.update(zip(capas[-1], nombres_salida))

    plt.rcParams.update({'font.family': 'sans-serif',
                         'font.sans-serif': ['Calibri', 'Carlito', 'Arial', 'DejaVu Sans'],
                         'font.size': 8})
    fig, ax = plt.subplots(figsize=(ancho_cm / 2.54, alto_cm / 2.54))
    for (a, b) in activas:
        if a not in pos or b not in pos:
            continue
        w = genoma.connections[(a, b)].weight
        color = ACENTO if w > 0 else NEGATIVO
        ax.annotate('', xy=pos[b], xytext=pos[a], arrowprops=dict(
            arrowstyle='->', lw=0.5 + 1.5 * min(abs(w), 3) / 3, color=color,
            shrinkA=9, shrinkB=9))
        # Valor del peso a un tercio del camino, para que no se solapen
        # en el nodo de llegada
        xm = pos[a][0] + (pos[b][0] - pos[a][0]) / 3
        ym = pos[a][1] + (pos[b][1] - pos[a][1]) / 3
        ax.text(xm, ym, '{:+.2f}'.format(w), fontsize=6, color=color,
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.1', fc='white', ec='none'))
    for n, (x, y) in pos.items():
        ax.scatter(x, y, s=260, color='#e8eaed', edgecolor=TINTA_2, lw=0.8,
                   zorder=3)
        if n in genoma.nodes:           # ocultos y salidas: sesgo dentro
            ax.text(x, y, '{:+.2f}'.format(genoma.nodes[n].bias), fontsize=5.5,
                    ha='center', va='center', color=TINTA, zorder=4)
        if n in capas[0]:
            ax.text(x - 0.12, y, nombres[n], ha='right', va='center',
                    fontsize=8, color=TINTA)
        elif n in capas[-1]:
            ax.text(x + 0.12, y, nombres[n], ha='left', va='center',
                    fontsize=8, color=TINTA)
        else:
            ax.text(x, y - 0.3, 'oculto {}'.format(n), ha='center',
                    va='top', fontsize=7, color=TINTA_2)
    ax.set_xlim(-0.9, len(capas) - 1 + 0.9)
    ax.axis('off')
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta) or '.', exist_ok=True)
    fig.savefig(ruta, dpi=300, bbox_inches='tight')


def main():
    p = argparse.ArgumentParser(description='Topología de la red de un genoma.')
    p.add_argument('--genoma', required=True,
                   help='evoluciones/<etiqueta>/genomas/mejor_genNNN.pkl')
    p.add_argument('--salida', required=True, help='PNG de salida')
    args = p.parse_args()

    # config-p2.ini y entorno.json de la evolución del genoma
    # genomas/mejor_genNNN.pkl o mejor_genoma.pkl, en la carpeta de la
    # evolución: se busca config-p2.ini al lado o un nivel por encima
    carpeta = os.path.dirname(os.path.abspath(args.genoma))
    if not os.path.exists(os.path.join(carpeta, 'config-p2.ini')):
        carpeta = os.path.dirname(carpeta)
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         os.path.join(carpeta, 'config-p2.ini'))
    with open(os.path.join(carpeta, 'entorno.json')) as f:
        entradas = ENTRADAS if json.load(f).get('obs_delta') else ENTRADAS[:5]
    with open(args.genoma, 'rb') as f:
        genoma = pickle.load(f)

    nombres = dict(zip(config.genome_config.input_keys, entradas))
    nombres.update(zip(config.genome_config.output_keys, SALIDAS))
    nodos, conexiones = genoma.size()
    print('Genoma {} (calidad {:.1f}): {} nodos, {} conexiones activas'.format(
        genoma.key, genoma.fitness or 0, nodos, conexiones))
    print('\nSesgos (salida de cada nodo: tanh(2,5·(sesgo + Σ peso·entrada))):')
    for n, nodo in sorted(genoma.nodes.items()):
        print('  {:12s} {:+.3f}'.format(nombres.get(n, 'oculto {}'.format(n)),
                                        nodo.bias))
    print('\nConexiones activas:')
    for c in sorted(genoma.connections.values(), key=lambda c: c.key):
        if c.enabled:
            a, b = c.key
            print('  {:14s} -> {:12s} {:+.3f}'.format(
                nombres.get(a, 'oculto {}'.format(a)),
                nombres.get(b, 'oculto {}'.format(b)), c.weight))

    dibujar_red(genoma, config, entradas, SALIDAS, args.salida)
    print('\nFigura guardada en {}'.format(args.salida))


if __name__ == '__main__':
    main()
