#!/usr/bin/env python3
"""
Práctica 1 — Curvas de aprendizaje a partir de los monitores de SB3.

Cumple los requisitos del apartado 8.1 del enunciado:
  - Magnitudes: recompensa acumulada por episodio y duración del episodio
    (dos paneles que comparten el eje horizontal).
  - Eje horizontal: pasos del entorno (suma acumulada de la columna l del
    monitor), no episodios ni tiempo de reloj.
  - Suavizado: media móvil de --ventana episodios, con la serie sin suavizar
    detrás en trazo tenue.
  - Semillas: media entre semillas y banda mínimo-máximo de las series
    suavizadas, interpoladas sobre una rejilla común de pasos.
  - Referencia: línea horizontal con la recompensa media por episodio de la
    política aleatoria en el mismo entorno (--aleatoria; se obtiene con
    train.py --aleatorio).
  - Origen de los datos: p1_logs/monitor_<alg>_<etiqueta>.monitor.csv.

Uso:
  python3 curvas.py --etiquetas c1_s1 c1_s2 c1_s3 --salida figuras/curva_c1.png \\
      --aleatoria -18.6 --pasos-max 200
  python3 curvas.py --etiquetas c3_tilt100_s1 c3_tilt100_s2 --salida figuras/curva_c3.png \\
      --pasos-max 300

Sin --aleatoria no se dibuja la referencia (avisa por pantalla).
"""

import argparse
import csv
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RUTA_LOGS = 'p1_logs'

# Grises primero; un único acento (azul) para la media entre semillas.
ACENTO = '#2a6fdb'
GRIS_SERIE = '#9aa0a6'
GRIS_REF = '#5f6368'
TINTA = '#202124'
TINTA_2 = '#5f6368'


def leer_monitor(ruta):
    """(pasos acumulados al final de cada episodio, recompensa, duración)."""
    with open(ruta) as f:
        next(f)                                  # línea de cabecera de SB3 (#{...})
        filas = list(csv.DictReader(f))
    r = np.array([float(x['r']) for x in filas])
    l = np.array([int(x['l']) for x in filas])
    return np.cumsum(l), r, l


def media_movil(y, ventana):
    """Media de los últimos `ventana` episodios (ventana más corta al principio)."""
    c = np.cumsum(np.insert(y.astype(float), 0, 0.0))
    n = np.arange(1, len(y) + 1)
    w = np.minimum(n, ventana)
    return (c[n] - c[n - w]) / w


def main():
    p = argparse.ArgumentParser(description='Curvas de aprendizaje (apartado 8.1).')
    p.add_argument('--etiquetas', nargs='+', required=True,
                   help='etiquetas de entrenamiento, una por semilla (c1_s1 c1_s2 ...)')
    p.add_argument('--algoritmo', default='sac')
    p.add_argument('--ventana', type=int, default=10,
                   help='episodios de la media móvil')
    p.add_argument('--aleatoria', type=float, default=None,
                   help='recompensa media por episodio de la política aleatoria')
    p.add_argument('--aleatoria-len', type=float, default=None,
                   help='duración media del episodio de la política aleatoria (pasos)')
    p.add_argument('--pasos-max', type=int, default=None,
                   help='límite de pasos por episodio, dibujado en el panel de duración')
    p.add_argument('--salida', required=True, help='PNG de salida')
    p.add_argument('--ancho-cm', type=float, default=16.0)
    p.add_argument('--alto-cm', type=float, default=6.5)
    args = p.parse_args()

    series = []
    for e in args.etiquetas:
        ruta = os.path.join(RUTA_LOGS, 'monitor_{}_{}.monitor.csv'.format(args.algoritmo, e))
        x, r, l = leer_monitor(ruta)
        series.append(dict(etiqueta=e, x=x, r=r, l=l,
                           rs=media_movil(r, args.ventana),
                           ls=media_movil(l, args.ventana)))
        print('{}: {} episodios, {} pasos'.format(e, len(r), x[-1]))

    # Rejilla común hasta los pasos de la semilla más corta: la media y la
    # banda solo se calculan donde existen todas las semillas.
    x_fin = min(s['x'][-1] for s in series)
    x_ini = max(s['x'][0] for s in series)
    rejilla = np.linspace(x_ini, x_fin, 400)

    plt.rcParams.update({'font.family': 'sans-serif',
                         'font.sans-serif': ['Calibri', 'Carlito', 'Arial', 'DejaVu Sans'],
                         'font.size': 8, 'axes.edgecolor': '#c4c7c5',
                         'axes.labelcolor': TINTA, 'xtick.color': TINTA_2,
                         'ytick.color': TINTA_2})
    fig, (ax_r, ax_l) = plt.subplots(
        1, 2, figsize=(args.ancho_cm / 2.54, args.alto_cm / 2.54), sharex=True)

    for ax, cruda, suav, nombre, unidad in (
            (ax_r, 'r', 'rs', 'Recompensa por episodio', '(adimensional)'),
            (ax_l, 'l', 'ls', 'Duración del episodio', '(pasos de ≈ 0,43 s)')):
        # Serie sin suavizar de cada semilla, tenue
        for s in series:
            ax.plot(s['x'], s[cruda], color=GRIS_SERIE, lw=0.5, alpha=0.35, zorder=1)
        # Media y banda mín-máx de las series suavizadas
        inter = np.array([np.interp(rejilla, s['x'], s[suav]) for s in series])
        if len(series) > 1:
            ax.fill_between(rejilla, inter.min(0), inter.max(0), color=ACENTO,
                            alpha=0.18, lw=0, zorder=2)
        ax.plot(rejilla, inter.mean(0), color=ACENTO, lw=1.6, zorder=3)
        ax.set_title('{} {}'.format(nombre, unidad), fontsize=8, color=TINTA, loc='left')
        ax.grid(axis='y', color='#e8eaed', lw=0.6)
        ax.set_axisbelow(True)
        for lado in ('top', 'right'):
            ax.spines[lado].set_visible(False)
        ax.set_xlabel('Pasos del entorno')
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: '{:,.0f}'.format(v).replace(',', ' ')))

    # Referencias, en gris y etiquetadas sobre la propia línea
    if args.aleatoria is not None:
        ax_r.axhline(args.aleatoria, color=GRIS_REF, lw=1, ls='--', zorder=2)
        ax_r.annotate('Política aleatoria ({:.1f})'.format(args.aleatoria).replace('.', ','),
                      xy=(rejilla[-1], args.aleatoria), xytext=(0, 3),
                      textcoords='offset points', ha='right', va='bottom',
                      fontsize=7, color=GRIS_REF)
    else:
        print('[aviso] Sin --aleatoria: falta la línea de referencia de la política aleatoria.')
    if args.aleatoria_len is not None:
        ax_l.axhline(args.aleatoria_len, color=GRIS_REF, lw=1, ls='--', zorder=2)
        ax_l.annotate('Aleatoria', xy=(rejilla[-1], args.aleatoria_len), xytext=(0, 3),
                      textcoords='offset points', ha='right', va='bottom',
                      fontsize=7, color=GRIS_REF)
    if args.pasos_max:
        ax_l.axhline(args.pasos_max, color=GRIS_REF, lw=0.8, ls=':', zorder=2)
        # Etiqueta encima de la línea, para no taparla cuando la curva llega
        # al límite
        ax_l.set_ylim(top=args.pasos_max * 1.12)
        ax_l.annotate('Límite del episodio ({})'.format(args.pasos_max),
                      xy=(rejilla[0], args.pasos_max), xytext=(0, 2),
                      textcoords='offset points', ha='left', va='bottom',
                      fontsize=7, color=GRIS_REF)

    # Leyenda única: qué es la línea azul, la banda y el gris
    n = len(series)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    leyenda = [Line2D([], [], color=ACENTO, lw=1.6,
                      label=('Media de {} semillas, media móvil de {} ep.'.format(n, args.ventana)
                             if n > 1 else 'Media móvil de {} ep.'.format(args.ventana)))]
    if n > 1:
        leyenda.append(Patch(color=ACENTO, alpha=0.18, lw=0, label='Mínimo–máximo entre semillas'))
    leyenda.append(Line2D([], [], color=GRIS_SERIE, lw=0.8, label='Sin suavizar'))
    fig.legend(handles=leyenda, loc='lower center', ncol=len(leyenda), frameon=False,
               fontsize=7, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    os.makedirs(os.path.dirname(args.salida) or '.', exist_ok=True)
    fig.savefig(args.salida, dpi=300)
    print('Figura guardada en {}'.format(args.salida))


if __name__ == '__main__':
    main()
