#!/usr/bin/env python3
"""
Práctica 2 — Curvas de la evolución a partir de evoluciones/<etiqueta>/evolucion.csv.

La figura conjunta tiene dos paneles que comparten el eje horizontal
(generaciones, o pasos del entorno acumulados con --eje pasos, para comparar
con las curvas de la P1):
  - Calidad (arriba): la del mejor individuo de cada generación (cada
    individuo se evalúa en un episodio, así que es ruidosa) y la media de la
    población con su desviación típica como banda. Línea de referencia en
    100, el máximo de la función de calidad, y, con --referencia, la calidad
    del controlador programado a mano.
  - Especiación (abajo): individuos de cada especie en áreas apiladas
    (columna tam_especies del CSV).

Con --por-config se guarda además una figura de calidad por cada configuración
del guía, con el nombre de la salida más _c1, _c2, etc. Todas usan la misma
escala vertical para que se puedan comparar.

Con varias etiquetas (semillas) se dibuja la media entre ellas, con la banda
mínimo-máximo para el mejor individuo, hasta la generación de la evolución
más corta; la especiación es la de la primera etiqueta. Si el guía cambia a
mitad de evolución (evolución incremental) se marca con una línea vertical
discontinua, y si solo cambia la duración del episodio, con una punteada: la
calidad se divide entre los pasos máximos, así que no es comparable a través
de ese cambio.

Imprime además los datos del pie de la figura que pide el enunciado
(población, episodios por individuo, duración máxima, pasos y horas) y la
complejidad del mejor genoma de la última generación.

Uso:
  python3 curvas_p2.py --etiquetas c1_s2 --salida figuras/evolucion_c1_s2.png
  python3 curvas_p2.py --etiquetas inc_s2 inc_s3 --referencia 60 --por-config \\
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
from matplotlib.ticker import FuncFormatter, MaxNLocator

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

NOMBRES_GUIA = {'c1': 'C1 (Crucero 10-10)', 'c2': 'C2 (Crucero 10-40)',
                'c3': 'C3 (Variable 10-40)',
                'c4': 'C4 (Variable con paradas 10-40)'}
ANCHO_ETAPA_CM = 8.0            # dos figuras caben una al lado de la otra
ALTO_ETAPA_CM = 6.5


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
                guia=np.array([x['guia'] for x in filas]),
                pasos_max=col('pasos_max', int),
                pasos=col('pasos'), segundos=col('segundos'),
                evaluaciones=col('evaluaciones', int),
                mejor=col('cal_mejor'), media=col('cal_media'),
                desv=col('cal_desv'), especies=especies,
                nodos=col('nodos_mejor', int),
                conexiones=col('conexiones_mejor', int),
                poblacion=ini.getint('NEAT', 'pop_size'))


def de_guia(s, guia):
    """Copia de la evolución s con sólo las generaciones de ese guía."""
    indices = np.flatnonzero(s['guia'] == guia)
    tramo = dict(s)
    for k, v in s.items():
        if isinstance(v, np.ndarray):
            tramo[k] = v[indices]
    tramo['especies'] = [s['especies'][i] for i in indices]
    return tramo


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
            '{:.1f} h. Mejor genoma final: {} nodos y {} conexiones '
            'activas'.format(s['etiqueta'], s['poblacion'], texto_dur,
                             len(s['gen']), s['evaluaciones'][-1],
                             s['pasos'][-1], s['segundos'][-1] / 3600,
                             s['nodos'][-1], s['conexiones'][-1]))


def eje_horizontal(series, n_gen, eje):
    """Valores y nombre del eje horizontal."""
    if eje == 'pasos':
        return np.mean([s['pasos'][:n_gen] for s in series], axis=0), 'Pasos del entorno'
    return series[0]['gen'][:n_gen], 'Generación'


def dibujar_calidad(ax, x, series, n_gen, referencia):
    """Media de la población con ±1 desviación típica (gris) y mejor
    individuo (acento), con la banda mínimo-máximo entre semillas."""
    media, _, _ = media_semillas(series, 'media', n_gen)
    desv, _, _ = media_semillas(series, 'desv', n_gen)
    ax.fill_between(x, np.clip(media - desv, -10, 100),
                    np.clip(media + desv, -10, 100),
                    color=GRIS_SERIE, alpha=0.22, lw=0, zorder=2)
    ax.plot(x, media, color=GRIS_SERIE, lw=1.2, zorder=3)
    mejor, mejor_min, mejor_max = media_semillas(series, 'mejor', n_gen)
    if len(series) > 1:
        ax.fill_between(x, mejor_min, mejor_max, color=ACENTO, alpha=0.18,
                        lw=0, zorder=2)
    ax.plot(x, mejor, color=ACENTO, lw=1.6, zorder=4)
    ax.axhline(100, color=GRIS_REF, lw=0.8, ls=':', zorder=2)
    if referencia is not None:
        ax.axhline(referencia, color=GRIS_REF, lw=0.8, ls='--', zorder=2)
        ax.annotate('Controlador programado a mano ({:.1f})'.format(referencia),
                    xy=(x[-1], referencia), xytext=(0, 2),
                    textcoords='offset points', ha='right', va='bottom',
                    fontsize=7, color=GRIS_REF)
    ax.set_ylim(-12, 118)
    ax.set_ylabel('Calidad')


def marcar_cambios(ax_q, ejes, x, guias, pasos_max):
    """Líneas verticales y etiquetas en los cambios de guía o de duración."""
    def marcar(i, texto):
        ax_q.annotate(texto, xy=(x[i], 1), xycoords=ax_q.get_xaxis_transform(),
                      xytext=(2, -2), textcoords='offset points', va='top',
                      fontsize=7, color=GRIS_REF)

    def texto_tramo(i, con_guia, con_pasos):
        partes = [guias[i].upper()] if con_guia else []
        if con_pasos:
            partes.append('{} pasos'.format(pasos_max[i]))
        return ' · '.join(partes)

    varios_guias = len(set(guias)) > 1
    hay_cambios = False
    for i in range(1, len(x)):
        otro_guia = guias[i] != guias[i - 1]
        otros_pasos = pasos_max[i] != pasos_max[i - 1]
        if not (otro_guia or otros_pasos):
            continue
        hay_cambios = True
        for ax in ejes:
            ax.axvline(x[i], color=GRIS_REF, lw=0.8,
                       ls='--' if otro_guia else ':', zorder=5)
        marcar(i, texto_tramo(i, otro_guia, otros_pasos))
    if hay_cambios:
        marcar(0, texto_tramo(0, varios_guias, True))


def estilo(ax, eje):
    ax.grid(axis='y', color='#e8eaed', lw=0.6)
    ax.set_axisbelow(True)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    if eje == 'pasos':
        ax.xaxis.set_major_formatter(FuncFormatter(
            lambda v, _: '{:,.0f}'.format(v).replace(',', ' ')))
    else:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, steps=(1, 2, 5, 10)))


def poner_leyenda(fig, n, ncol, corta=False):
    """Leyenda fuera de los paneles, para que no tape los datos."""
    sufijo = ''
    if n > 1:
        sufijo = ' (media)' if corta else ' (media de {} semillas)'.format(n)
    leyenda = [Line2D([], [], color=ACENTO, lw=1.6,
                      label='Mejor individuo' + sufijo)]
    if n > 1:
        leyenda.append(Patch(color=ACENTO, alpha=0.18, lw=0,
                             label='Mínimo–máximo entre semillas'))
    leyenda += [Line2D([], [], color=GRIS_SERIE, lw=1.2,
                       label='Media de la población' + ('' if corta else sufijo)),
                Patch(color=GRIS_SERIE, alpha=0.22, lw=0,
                      label='±1 desviación típica'),
                Line2D([], [], color=GRIS_REF, lw=0.8, ls=':',
                       label='Máximo (100)' if corta else 'Máximo de la calidad (100)')]
    fig.legend(handles=leyenda, loc='upper center', frameon=False, fontsize=7,
               ncol=ncol, columnspacing=1.4)


def guardar(fig, ruta):
    os.makedirs(os.path.dirname(ruta) or '.', exist_ok=True)
    fig.savefig(ruta, dpi=300)
    plt.close(fig)
    print('Figura guardada en {}'.format(ruta))


def figura_conjunta(series, args):
    """Calidad y especiación de toda la evolución."""
    n_gen = min(len(s['gen']) for s in series)
    n = len(series)
    x, nombre_x = eje_horizontal(series, n_gen, args.eje)
    fig, (ax_q, ax_e) = plt.subplots(
        2, 1, sharex=True, gridspec_kw={'height_ratios': (2, 1)},
        figsize=(args.ancho_cm / 2.54, args.alto_cm / 2.54))

    dibujar_calidad(ax_q, x, series, n_gen, args.referencia)
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
    ax_e.set_xlabel(nombre_x)
    ax_e.set_title('Individuos por especie' + (
        ' ({})'.format(series[0]['etiqueta']) if n > 1 else ''),
        fontsize=8, color=TINTA, loc='left')

    marcar_cambios(ax_q, (ax_q, ax_e), x, series[0]['guia'][:n_gen],
                   series[0]['pasos_max'][:n_gen])
    for ax in (ax_q, ax_e):
        estilo(ax, args.eje)
    poner_leyenda(fig, n, 3)
    fig.tight_layout(rect=(0, 0, 1, 0.90 if n > 1 else 0.93))
    guardar(fig, args.salida)


def figura_etapa(series, guia, args):
    """Calidad durante las generaciones de un guía."""
    tramos = [de_guia(s, guia) for s in series]
    tramos = [t for t in tramos if len(t['gen'])]
    if not tramos:
        return
    n_gen = min(len(t['gen']) for t in tramos)
    n = len(tramos)
    x, nombre_x = eje_horizontal(tramos, n_gen, args.eje)
    fig, ax = plt.subplots(figsize=(ANCHO_ETAPA_CM / 2.54, ALTO_ETAPA_CM / 2.54))

    dibujar_calidad(ax, x, tramos, n_gen, args.referencia)
    duraciones = sorted(set(tramos[0]['pasos_max'][:n_gen]))
    ax.set_title('{}, {} pasos'.format(
        NOMBRES_GUIA.get(guia, guia.upper()),
        ' y '.join(str(d) for d in duraciones)),
        fontsize=8, color=TINTA, loc='left')
    ax.set_xlabel(nombre_x)
    marcar_cambios(ax, (ax,), x, tramos[0]['guia'][:n_gen],
                   tramos[0]['pasos_max'][:n_gen])
    estilo(ax, args.eje)
    poner_leyenda(fig, n, 2, corta=True)
    fig.tight_layout(rect=(0, 0, 1, 0.81 if n > 1 else 0.87))

    base, extension = os.path.splitext(args.salida)
    guardar(fig, '{}_{}{}'.format(base, guia, extension))


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
    p.add_argument('--por-config', action='store_true',
                   help='guarda además una figura de calidad por cada guía')
    p.add_argument('--salida', required=True, help='PNG de salida')
    p.add_argument('--ancho-cm', type=float, default=16.0)
    p.add_argument('--alto-cm', type=float, default=9.5)
    args = p.parse_args()

    series = [leer_evolucion(e) for e in args.etiquetas]
    print('Pie de la figura:')
    for s in series:
        print('  ' + pie(s))

    plt.rcParams.update({'font.family': 'sans-serif',
                         'font.sans-serif': ['Calibri', 'Carlito', 'Arial', 'DejaVu Sans'],
                         'font.size': 8, 'axes.edgecolor': '#c4c7c5',
                         'axes.labelcolor': TINTA, 'xtick.color': TINTA_2,
                         'ytick.color': TINTA_2})
    figura_conjunta(series, args)
    if args.por_config:
        for guia in dict.fromkeys(g for s in series for g in s['guia']):
            figura_etapa(series, guia, args)


if __name__ == '__main__':
    main()
