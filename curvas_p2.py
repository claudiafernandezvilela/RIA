#!/usr/bin/env python3
"""
Práctica 2 — Curvas de la evolución a partir de evoluciones/<etiqueta>/evolucion.csv.

Tres paneles que comparten el eje horizontal (generaciones, o pasos del
entorno acumulados con --eje pasos, para comparar con las curvas de la P1):
  - Calidad (arriba): la del mejor individuo de cada generación (cada
    individuo se evalúa en un episodio, así que es ruidosa) y la media de la
    población con su desviación típica como banda. Línea de referencia en
    100, el máximo de la función de calidad, y, con --referencia, la calidad
    del controlador programado a mano.
  - Especiación (abajo a la izquierda): individuos de cada especie en áreas
    apiladas (columna tam_especies del CSV).
  - Complejidad (abajo a la derecha): nodos y conexiones activas del mejor
    genoma.

Con varias etiquetas (semillas) se dibuja la media entre ellas, con la banda
mínimo-máximo para el mejor individuo, hasta la generación de la evolución
más corta; la especiación es la de la primera etiqueta. Si el guía cambia a
mitad de evolución (evolución incremental) se marca con una línea vertical.

Imprime además los datos del pie de la figura que pide el enunciado
(población, episodios por individuo, duración máxima, pasos y horas).

Uso:
  python3 curvas_p2.py --etiquetas c1_s2 --salida figuras/evolucion_c1_s2.png
  python3 curvas_p2.py --etiquetas inc_s2 inc_s3 --referencia 60 \\
                       --salida figuras/evolucion_inc.png
"""

import argparse
import configparser
import csv
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

RUTA_EVOLUCIONES = 'evoluciones'
SEGUNDOS_POR_PASO = 0.37        # medido en las evoluciones de C1

# Los mismos colores que curvas.py: grises y un único acento azul
ACENTO = '#2a6fdb'
GRIS_SERIE = '#9aa0a6'
GRIS_REF = '#5f6368'
TINTA = '#202124'
TINTA_2 = '#5f6368'
# Especies: tonos de azul y gris alternados (sólo hay que distinguir vecinas)
COLORES_ESPECIES = ['#2a6fdb', '#9aa0a6', '#7fa8ea', '#5f6368', '#c4d6f5',
                    '#c4c7c5']


def leer_evolucion(etiqueta):
    """Columnas de evolucion.csv como arrays, una fila por generación, y el
    tamaño de la población de config-p2.ini."""
    carpeta = os.path.join(RUTA_EVOLUCIONES, etiqueta)
    with open(os.path.join(carpeta, 'evolucion.csv')) as f:
        filas = list(csv.DictReader(f))
    ini = configparser.ConfigParser()
    ini.read(os.path.join(carpeta, 'config-p2.ini'))
    col = lambda k, t=float: np.array([t(x[k]) for x in filas])
    # tam_especies: 'id:n;id:n;...' -> {id: n} por generación
    especies = [dict(map(int, par.split(':')) for par in x['tam_especies'].split(';'))
                for x in filas]
    return dict(etiqueta=etiqueta, gen=col('generacion', int),
                guia=[x['guia'] for x in filas], pasos_max=col('pasos_max', int),
                pasos=col('pasos'), segundos=col('segundos'),
                evaluaciones=col('evaluaciones', int),
                mejor=col('cal_mejor'), media=col('cal_media'),
                desv=col('cal_desv'), especies=especies,
                nodos=col('nodos_mejor'), conexiones=col('conexiones_mejor'),
                poblacion=ini.getint('NEAT', 'pop_size'))


def media_semillas(series, clave, n):
    """(media, mínimo, máximo) entre semillas de las n primeras generaciones."""
    y = np.array([s[clave][:n] for s in series])
    return y.mean(0), y.min(0), y.max(0)


def pie(s):
    """Datos del pie de la figura de una evolución."""
    duraciones = sorted(set(s['pasos_max']))
    texto_dur = ' y '.join('{} pasos (~{:.0f} s)'.format(
        d, d * SEGUNDOS_POR_PASO) for d in duraciones)
    return ('{}: población {}, 1 episodio por individuo, duración máxima {}, '
            '{} generaciones, {} evaluaciones, {:.0f} pasos del entorno, '
            '{:.1f} h'.format(s['etiqueta'], s['poblacion'], texto_dur,
                              len(s['gen']), s['evaluaciones'][-1],
                              s['pasos'][-1], s['segundos'][-1] / 3600))


def main():
    p = argparse.ArgumentParser(description='Curvas de la evolución (P2).')
    p.add_argument('--etiquetas', nargs='+', required=True,
                   help='evoluciones, una por semilla (c1_s1 c1_s2 ...)')
    p.add_argument('--eje', choices=['generaciones', 'pasos'],
                   default='generaciones',
                   help='eje horizontal: generación o pasos del entorno '
                        'acumulados (media entre semillas)')
    p.add_argument('--referencia', type=float, default=None,
                   help='calidad del controlador programado a mano (línea '
                        'horizontal)')
    p.add_argument('--salida', required=True, help='PNG de salida')
    p.add_argument('--ancho-cm', type=float, default=16.0)
    p.add_argument('--alto-cm', type=float, default=11.0)
    args = p.parse_args()

    series = [leer_evolucion(e) for e in args.etiquetas]
    print('Pie de la figura:')
    for s in series:
        print('  ' + pie(s))

    n_gen = min(len(s['gen']) for s in series)
    if args.eje == 'pasos':
        x = np.mean([s['pasos'][:n_gen] for s in series], axis=0)
        nombre_x = 'Pasos del entorno'
    else:
        x = series[0]['gen'][:n_gen]
        nombre_x = 'Generación'

    plt.rcParams.update({'font.family': 'sans-serif',
                         'font.sans-serif': ['Calibri', 'Carlito', 'Arial', 'DejaVu Sans'],
                         'font.size': 8, 'axes.edgecolor': '#c4c7c5',
                         'axes.labelcolor': TINTA, 'xtick.color': TINTA_2,
                         'ytick.color': TINTA_2})
    fig = plt.figure(figsize=(args.ancho_cm / 2.54, args.alto_cm / 2.54))
    rejilla = fig.add_gridspec(2, 2, height_ratios=(1.25, 1))
    ax_q = fig.add_subplot(rejilla[0, :])
    ax_e = fig.add_subplot(rejilla[1, 0], sharex=ax_q)
    ax_c = fig.add_subplot(rejilla[1, 1], sharex=ax_q)
    n = len(series)

    # Calidad: media de la población con ±1 desviación típica (gris) y
    # mejor individuo (acento), con la banda mínimo-máximo entre semillas
    media, _, _ = media_semillas(series, 'media', n_gen)
    desv, _, _ = media_semillas(series, 'desv', n_gen)
    ax_q.fill_between(x, np.clip(media - desv, -10, 100),
                      np.clip(media + desv, -10, 100),
                      color=GRIS_SERIE, alpha=0.22, lw=0, zorder=2)
    ax_q.plot(x, media, color=GRIS_SERIE, lw=1.2, zorder=3)
    mejor, mejor_min, mejor_max = media_semillas(series, 'mejor', n_gen)
    if n > 1:
        ax_q.fill_between(x, mejor_min, mejor_max, color=ACENTO, alpha=0.18,
                          lw=0, zorder=2)
    ax_q.plot(x, mejor, color=ACENTO, lw=1.6, zorder=4)
    ax_q.axhline(100, color=GRIS_REF, lw=0.8, ls=':', zorder=2)
    ax_q.annotate('Máximo de la calidad (100)', xy=(x[0], 100), xytext=(0, 2),
                  textcoords='offset points', ha='left', va='bottom',
                  fontsize=7, color=GRIS_REF)
    if args.referencia is not None:
        ax_q.axhline(args.referencia, color=GRIS_REF, lw=0.8, ls='--', zorder=2)
        ax_q.annotate('Controlador programado a mano ({:.1f})'.format(
                          args.referencia),
                      xy=(x[-1], args.referencia), xytext=(0, 2),
                      textcoords='offset points', ha='right', va='bottom',
                      fontsize=7, color=GRIS_REF)
    ax_q.set_ylim(-12, 112)
    ax_q.set_ylabel('Calidad')
    ax_q.set_title('Calidad (entre −10 y 100)', fontsize=8, color=TINTA, loc='left')

    # Especiación: individuos por especie, apilados (primera semilla)
    esp = series[0]['especies'][:n_gen]
    ids = sorted({sid for g in esp for sid in g})
    tam = np.array([[g.get(sid, 0) for g in esp] for sid in ids])
    ax_e.stackplot(x, tam, colors=[COLORES_ESPECIES[i % len(COLORES_ESPECIES)]
                                   for i in range(len(ids))],
                   edgecolor='white', lw=0.4)
    ax_e.set_ylim(0, series[0]['poblacion'])
    ax_e.set_ylabel('Individuos')
    ax_e.set_title('Individuos por especie' + (
        ' ({})'.format(series[0]['etiqueta']) if n > 1 else ''),
        fontsize=8, color=TINTA, loc='left')

    # Complejidad del mejor: nodos (acento) y conexiones activas (gris)
    ax_c.plot(x, media_semillas(series, 'nodos', n_gen)[0], color=ACENTO,
              lw=1.6, label='Nodos')
    ax_c.plot(x, media_semillas(series, 'conexiones', n_gen)[0],
              color=GRIS_SERIE, lw=1.2, label='Conexiones activas')
    ax_c.set_ylim(bottom=0)
    ax_c.set_title('Complejidad del mejor genoma', fontsize=8, color=TINTA,
                   loc='left')
    ax_c.legend(loc='center right', frameon=False, fontsize=7)

    # Cambio de configuración del guía (evolución incremental)
    guias = series[0]['guia'][:n_gen]
    for i in range(1, n_gen):
        if guias[i] != guias[i - 1]:
            for ax in (ax_q, ax_e, ax_c):
                ax.axvline(x[i], color=GRIS_REF, lw=0.8, ls='--', zorder=5)
            ax_q.annotate(guias[i].upper(), xy=(x[i], 100), xytext=(2, -10),
                          textcoords='offset points', fontsize=7, color=GRIS_REF)

    for ax in (ax_q, ax_e, ax_c):
        ax.grid(axis='y', color='#e8eaed', lw=0.6)
        ax.set_axisbelow(True)
        for lado in ('top', 'right'):
            ax.spines[lado].set_visible(False)
        if args.eje == 'pasos':
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
                lambda v, _: '{:,.0f}'.format(v).replace(',', ' ')))
    for ax in (ax_e, ax_c):
        ax.set_xlabel(nombre_x)

    sufijo = ' (media de {} semillas)'.format(n) if n > 1 else ''
    leyenda = [Line2D([], [], color=ACENTO, lw=1.6,
                      label='Mejor individuo' + sufijo)]
    if n > 1:
        leyenda.append(Patch(color=ACENTO, alpha=0.18, lw=0,
                             label='Mínimo–máximo entre semillas'))
    leyenda += [Line2D([], [], color=GRIS_SERIE, lw=1.2,
                       label='Media de la población' + sufijo),
                Patch(color=GRIS_SERIE, alpha=0.22, lw=0,
                      label='±1 desviación típica de la población')]
    ax_q.legend(handles=leyenda, loc='lower right', frameon=False, fontsize=7,
                ncol=2 if n > 1 else 1)
    fig.tight_layout()

    os.makedirs(os.path.dirname(args.salida) or '.', exist_ok=True)
    fig.savefig(args.salida, dpi=300)
    print('Figura guardada en {}'.format(args.salida))


if __name__ == '__main__':
    main()
