#!/usr/bin/env python3
"""
Práctica 2 — Ejemplo XOR de NEAT-Python 2.0 (comprobación de la imagen).

Es el evolve-feedforward.py de los ejemplos oficiales (examples/xor, v2.0.0)
con dos cambios para que funcione en el contenedor:

  - Las figuras se hacen con Matplotlib y se guardan en PNG, sin abrir
    ventanas ni usar graphviz (el visualize.py oficial lo importa y no está
    instalado en la imagen).
  - Los puntos de control van a la carpeta chk/ y, al final, se reanuda la
    evolución desde el último, que es lo mismo que habrá que hacer con las
    evoluciones largas del seguidor.

Uso, desde esta carpeta y dentro del contenedor:

    python3 xor_neat.py

Deja en resultados/ la curva de evolución, la especiación y la topología
de la red ganadora. El ejemplo oficial sin cambios es evolve-minimal.py
(python3 evolve-minimal.py), que sólo imprime por consola.
"""

import glob
import os

import matplotlib
matplotlib.use('Agg')            # sin pantalla: sólo se guardan archivos
import matplotlib.pyplot as plt
import numpy as np

import neat

DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG = os.path.join(DIR, 'config-feedforward')
DIR_CHK = os.path.join(DIR, 'chk')
DIR_RES = os.path.join(DIR, 'resultados')

# Tabla de verdad del XOR
XOR_ENTRADAS = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)]
XOR_SALIDAS = [(0.0,), (1.0,), (1.0,), (0.0,)]


def eval_genomes(genomas, config):
    """Calidad = 4 - suma de errores cuadráticos en los cuatro casos.
    Vale 4 con una red perfecta; el umbral de parada es 3,9."""
    for _, genoma in genomas:
        red = neat.nn.FeedForwardNetwork.create(genoma, config)
        genoma.fitness = 4.0
        for xi, xo in zip(XOR_ENTRADAS, XOR_SALIDAS):
            salida = red.activate(xi)
            genoma.fitness -= (salida[0] - xo[0]) ** 2


def curva_evolucion(estadisticas, ruta):
    """Mejor calidad y media de la población, con la desviación típica
    como banda."""
    gen = np.arange(len(estadisticas.most_fit_genomes))
    mejor = [g.fitness for g in estadisticas.most_fit_genomes]
    media = np.array(estadisticas.get_fitness_mean())
    desv = np.array(estadisticas.get_fitness_stdev())

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(gen, mejor, 'r-', label='Mejor')
    ax.plot(gen, media, 'b-', label='Media')
    ax.fill_between(gen, media - desv, media + desv, color='b', alpha=0.2,
                    label='Media ± desv. típica')
    ax.set_xlabel('Generación')
    ax.set_ylabel('Calidad (0-4)')
    ax.grid(True)
    ax.legend(loc='lower right')
    fig.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close(fig)


def especiacion(estadisticas, ruta):
    """Tamaño de cada especie por generación, en áreas apiladas."""
    tam = np.array(estadisticas.get_species_sizes()).T  # especies x generaciones
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.stackplot(range(tam.shape[1]), tam)
    ax.set_xlabel('Generación')
    ax.set_ylabel('Individuos por especie')
    fig.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close(fig)


def dibujar_red(genoma, config, nombres_entrada, nombres_salida, ruta):
    """Red por capas con Matplotlib (función de las indicaciones técnicas,
    apartado 7). Grosor proporcional al peso; verde positivo, rojo negativo."""
    gc = config.genome_config
    entradas, salidas = list(gc.input_keys), list(gc.output_keys)
    activas = [c.key for c in genoma.connections.values() if c.enabled]
    # Profundidad de cada nodo: camino más largo desde las entradas
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
    pos = {n: (i, j - (len(c) - 1) / 2)
           for i, c in enumerate(capas) for j, n in enumerate(c)}
    fig, ax = plt.subplots(figsize=(6, 4))
    for (a, b) in activas:
        if a in pos and b in pos:
            w = genoma.connections[(a, b)].weight
            ax.annotate('', xy=pos[b], xytext=pos[a], arrowprops=dict(
                arrowstyle='->', lw=0.5 + 1.5 * min(abs(w), 3) / 3,
                color='tab:green' if w > 0 else 'tab:red'))
    nombres = dict(zip(entradas, nombres_entrada))
    nombres.update(zip(salidas, nombres_salida))
    for n, (x, y) in pos.items():
        ax.scatter(x, y, s=300, color='lightgrey', edgecolor='black', zorder=3)
        ax.text(x, y + 0.25, nombres.get(n, str(n)), ha='center', fontsize=8)
    ax.axis('off')
    fig.savefig(ruta, dpi=200, bbox_inches='tight')
    plt.close(fig)


def main():
    os.makedirs(DIR_CHK, exist_ok=True)     # el Checkpointer no crea carpetas
    os.makedirs(DIR_RES, exist_ok=True)
    for viejo in glob.glob(os.path.join(DIR_CHK, 'xor-*')):
        os.remove(viejo)                     # que no se mezclen ejecuciones

    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         RUTA_CONFIG)

    poblacion = neat.Population(config)
    poblacion.add_reporter(neat.StdOutReporter(True))
    estadisticas = neat.StatisticsReporter()
    poblacion.add_reporter(estadisticas)
    poblacion.add_reporter(neat.Checkpointer(
        generation_interval=5, filename_prefix=os.path.join(DIR_CHK, 'xor-')))

    # Hasta 300 generaciones; para antes si se alcanza fitness_threshold
    ganador = poblacion.run(eval_genomes, 300)

    print('\nMejor genoma:\n{!s}'.format(ganador))
    print('\nSalida del mejor genoma:')
    red = neat.nn.FeedForwardNetwork.create(ganador, config)
    for xi, xo in zip(XOR_ENTRADAS, XOR_SALIDAS):
        salida = red.activate(xi)
        print('  entrada {!r}, esperada {!r}, obtenida {:.3f}'.format(
            xi, xo, salida[0]))
    nodos, conexiones = ganador.size()
    print('Tamaño: {} nodos (sin contar entradas), {} conexiones activas'
          .format(nodos, conexiones))

    curva_evolucion(estadisticas, os.path.join(DIR_RES, 'curva_xor.png'))
    especiacion(estadisticas, os.path.join(DIR_RES, 'especies_xor.png'))
    dibujar_red(ganador, config, ['A', 'B'], ['A XOR B'],
                os.path.join(DIR_RES, 'red_xor.png'))
    print('Figuras en {}'.format(DIR_RES))

    # Reanudar desde el último punto de control (el de número más alto).
    # Los registros no se guardan en el punto de control: se vuelven a añadir.
    chks = glob.glob(os.path.join(DIR_CHK, 'xor-*'))
    if chks:
        ultimo = max(chks, key=lambda r: int(r.rsplit('-', 1)[1]))
        print('\nReanudando desde {} durante 5 generaciones'.format(
            os.path.basename(ultimo)))
        poblacion = neat.Checkpointer.restore_checkpoint(ultimo)
        poblacion.add_reporter(neat.StdOutReporter(False))
        poblacion.run(eval_genomes, 5)


if __name__ == '__main__':
    main()
