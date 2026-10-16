#!/usr/bin/env python3
"""
Práctica 1 — Evaluador con el protocolo común (anexo B del enunciado).

Ejecuta una política (la aprendida, en modo determinista, o la aleatoria
como línea base) durante episodios de 120 s y la mide con la verdad del
simulador, con independencia de la recompensa:

  B.1  Pelota: pose del guía desplazada pelota_offset_m hacia atrás.
       Separación: distancia centro del seguidor - pelota.
       Desviación: ángulo entre el rumbo del seguidor y la dirección a la
       pelota.
  B.3  Fallos, comprobados en cada paso:
         colisión      separación < sep_colision_m (0,12 m)
         guía perdido  separación > sep_perdido_m (0,90 m), o la pelota
                       sin detectarse durante más de eval_sin_ver_s (3 s)
                       seguidos, medidos con el reloj y no en pasos
       Una terminación del entorno por otra causa (atasco) se registra
       como tal y no cuenta como completado.
  B.4  Registro por paso (CSV) y las cuatro métricas: completados,
       desenlaces, separación (% en banda y media) y desviación (media de
       |desv| y % por debajo de desv_max_grados).

Todos los umbrales están en config.json.

--------------------------------------------------------------------
USO
--------------------------------------------------------------------

  Para cada configuración del guía (anexo B.2), ponerla en RoboboSim
  con el mismo multiplicador de velocidad que en el entrenamiento:

      C1  Crucero   10 - 10
      C2  Crucero   10 - 40
      C3  Variable  10 - 40

  y lanzar (el puente como en train.py):

      python3 evaluar.py --config c1 --algoritmo sac --etiqueta c1
      python3 evaluar.py --config c1 --aleatorio          # línea base

  --etiqueta elige el modelo p1_modelo_<alg>_<etiqueta>.zip (como en
  train.py); --modelo permite dar la ruta directamente. Se evalúa con la
  configuración guardada junto al modelo (p1_modelo_<...>.json); para la
  aleatoria, o un modelo sin esa copia, con --config-json:

      python3 evaluar.py --config c1 --aleatorio --config-json config_c1.json

  Cuando estén todas las ejecuciones, las tablas de métricas:

      python3 evaluar.py --metricas

  Se generan en p1_eval/:
      <politica>_<config>_ep<n>.csv   registro por paso de cada episodio
      episodios.csv                   una fila por episodio (desenlace)
      metricas.md                     tablas del anexo B.4
"""

import argparse
import csv
import glob
import os
import time

import numpy as np


RUTA_EVAL = 'p1_eval'
CONFIGS = ('c1', 'c2', 'c3')
DESENLACES = ('completado', 'colisión', 'guía perdido', 'otra causa')

CAMPOS_PASO = ['t', 'paso', 'seguidor_x_mm', 'seguidor_z_mm',
               'seguidor_rot_grados', 'pelota_x_mm', 'pelota_z_mm',
               'separacion_m', 'desviacion_grados', 'visible', 'blob_x',
               'accion_0', 'accion_1', 'v_ms', 'w_rads']
CAMPOS_EPISODIO = ['politica', 'config', 'episodio', 'desenlace', 'detalle',
                   'duracion_s', 'pasos', 'fecha']


def _f(v):
    """Formato de una celda del CSV ('' si no hay dato)."""
    if v is None:
        return ''
    if isinstance(v, (bool, np.bool_)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return '{:.4f}'.format(float(v))
    return v


# ------------------------------------------------------------- ejecución

def ejecutar_episodio(env, politica, cfg, ruta_csv):
    """Un episodio del protocolo. Devuelve (desenlace, detalle, duracion,
    pasos)."""
    obs, _ = env.reset()
    t0 = time.time()
    t_ultima_vista = t0
    pasos = 0
    desenlace = detalle = None

    with open(ruta_csv, 'w', newline='') as f:
        esc = csv.writer(f)
        esc.writerow(CAMPOS_PASO)

        while True:
            accion = politica(obs)
            obs, _, terminado, truncado, info = env.step(accion)
            pasos += 1
            t = time.time() - t0

            pose = info.get('pose_sim') or (None, None, None)
            pelota = info.get('pelota_sim') or (None, None)
            sep = info.get('separacion')
            visible = info.get('visible', False)
            if visible:
                t_ultima_vista = time.time()

            esc.writerow([_f(v) for v in (
                t, pasos, pose[0], pose[1], pose[2], pelota[0], pelota[1],
                sep, info.get('desviacion'), visible, info.get('x'),
                float(accion[0]), float(accion[1]),
                info.get('v'), info.get('w'))])

            # Criterios de fallo del anexo B.3, comprobados aquí con la
            # verdad del terreno, no con lo que decida el entorno.
            sin_ver = time.time() - t_ultima_vista
            if sep is not None and sep < cfg['sep_colision_m']:
                desenlace, detalle = 'colisión', 'sep={:.3f} m'.format(sep)
            elif sep is not None and sep > cfg['sep_perdido_m']:
                desenlace, detalle = 'guía perdido', 'sep={:.3f} m'.format(sep)
            elif sin_ver > cfg['eval_sin_ver_s']:
                desenlace, detalle = ('guía perdido',
                                      'sin ver {:.1f} s'.format(sin_ver))
            elif terminado:
                # El entorno terminó por una causa propia (p. ej. atasco)
                causas = [k for k in ('atascado', 'choque', 'perdido')
                          if info.get(k)]
                desenlace = 'otra causa'
                detalle = 'entorno: ' + (','.join(causas) or 'desconocida')
            elif t >= cfg['eval_duracion_s']:
                desenlace, detalle = 'completado', ''
            elif truncado:
                desenlace = 'otra causa'
                detalle = 'entorno truncado antes de {} s'.format(
                    cfg['eval_duracion_s'])
            if desenlace is not None:
                break

    env._detener()
    return desenlace, detalle, time.time() - t0, pasos


def modo_ejecutar(args):
    from env import RoboboSeguirEnv, cargar_config
    from train import cargar_algoritmo, config_de_modelo

    # Configuración: la guardada junto al modelo (la de su entrenamiento),
    # porque la escala de la acción (v_min, v_max, w_max) tiene que ser
    # la misma. Para la política aleatoria, o un modelo antiguo sin copia,
    # config.json con --config-json encima.
    ruta = None
    if not args.aleatorio:
        ruta = args.modelo or 'p1_modelo_{}{}'.format(
            args.algoritmo, '_' + args.etiqueta if args.etiqueta else '')
        ruta = ruta[:-4] if ruta.endswith('.zip') else ruta
        if not os.path.exists(ruta + '.zip'):
            raise SystemExit('No existe {}.zip'.format(ruta))
    if ruta and os.path.exists(config_de_modelo(ruta)):
        # Los umbrales del protocolo se toman siempre de config.json
        cfg = dict(cargar_config(config_de_modelo(ruta)),
                   **{k: v for k, v in cargar_config().items()
                      if k.startswith(('eval_', 'banda_', 'desv_'))})
        print('Configuración del modelo: {}'.format(config_de_modelo(ruta)))
    else:
        cfg = cargar_config(extra=args.config_json)
        if ruta:
            print('[aviso] {} no tiene copia de su configuración; se usa '
                  'config.json{}. Comprobar que v_min, v_max y w_max son '
                  'los del entrenamiento.'.format(
                      ruta, ' + ' + args.config_json if args.config_json
                      else ''))

    # El fin por pelota no vista lo decide el evaluador con el reloj
    # (3 s, anexo B.3), no el entorno en pasos: se desactiva el de éste.
    # Tampoco debe truncar por pasos antes de los 120 s.
    cfg_env = dict(cfg, pasos_perdido_max=10 ** 9)
    env = RoboboSeguirEnv(pasos_max=10 ** 9, config=cfg_env,
                          verbose=args.detalle)

    try:
        if args.aleatorio:
            nombre = 'aleatoria'
            politica = lambda obs: env.action_space.sample()
        else:
            modelo = cargar_algoritmo(args.algoritmo, ruta, env)
            nombre = os.path.basename(ruta)
            # Política determinista (anexo B.2)
            politica = lambda obs: modelo.predict(obs, deterministic=True)[0]

        os.makedirs(RUTA_EVAL, exist_ok=True)
        ruta_ep = os.path.join(RUTA_EVAL, 'episodios.csv')
        nuevo = not os.path.exists(ruta_ep)

        print('\nEvaluando {} en {} ({} episodio/s de {:.0f} s)'.format(
            nombre, args.config.upper(), args.episodios,
            cfg['eval_duracion_s']))
        for ep in range(1, args.episodios + 1):
            ruta_csv = os.path.join(RUTA_EVAL, '{}_{}_ep{}.csv'.format(
                nombre, args.config, ep))
            desenlace, detalle, dur, pasos = ejecutar_episodio(
                env, politica, cfg, ruta_csv)
            print('episodio {}  {:6.1f} s  {:4d} pasos  {} {}'.format(
                ep, dur, pasos, desenlace, detalle))

            with open(ruta_ep, 'a', newline='') as f:
                esc = csv.writer(f)
                if nuevo:
                    esc.writerow(CAMPOS_EPISODIO)
                    nuevo = False
                esc.writerow([nombre, args.config, ep, desenlace, detalle,
                              '{:.2f}'.format(dur), pasos,
                              time.strftime('%Y-%m-%d %H:%M:%S')])
    finally:
        env.close()


# ------------------------------------------------------------- métricas

def _leer_pasos(ruta):
    """(separaciones, desviaciones) válidas de un CSV de pasos."""
    seps, desvs = [], []
    with open(ruta) as f:
        for fila in csv.DictReader(f):
            if fila['separacion_m'] != '':
                seps.append(float(fila['separacion_m']))
            if fila['desviacion_grados'] != '':
                desvs.append(float(fila['desviacion_grados']))
    return np.array(seps), np.array(desvs)


def calcular_metricas(episodios, cfg):
    """Métricas del anexo B.4 sobre una lista de filas de episodios.csv.
    Los porcentajes de separación y desviación se calculan sobre el total
    de pasos de todos los episodios del grupo."""
    n = len(episodios)
    cuenta = {d: 0 for d in DESENLACES}
    seps, desvs = [], []
    for e in episodios:
        cuenta[e['desenlace']] = cuenta.get(e['desenlace'], 0) + 1
        s, d = _leer_pasos(e['_csv'])
        seps.append(s)
        desvs.append(d)
    seps = np.concatenate(seps) if seps else np.array([])
    desvs = np.abs(np.concatenate(desvs)) if desvs else np.array([])

    def pct(x):
        return 100.0 * float(np.mean(x)) if len(x) else float('nan')

    return {
        'n': n,
        'completados': cuenta['completado'],
        'pct_completados': 100.0 * cuenta['completado'] / n if n else float('nan'),
        'desenlaces': cuenta,
        'pct_banda': pct((seps >= cfg['banda_min_m']) &
                         (seps <= cfg['banda_max_m'])),
        'sep_media': float(np.mean(seps)) if len(seps) else float('nan'),
        'desv_media': float(np.mean(desvs)) if len(desvs) else float('nan'),
        'pct_desv': pct(desvs < cfg['desv_max_grados']),
        'pasos': len(seps),
    }


def modo_metricas(args):
    import json
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'config.json')) as f:
        cfg = json.load(f)

    ruta_ep = os.path.join(RUTA_EVAL, 'episodios.csv')
    if not os.path.exists(ruta_ep):
        raise SystemExit('No hay {}. Hay que evaluar primero.'.format(ruta_ep))
    with open(ruta_ep) as f:
        episodios = list(csv.DictReader(f))
    for e in episodios:
        e['_csv'] = os.path.join(RUTA_EVAL, '{}_{}_ep{}.csv'.format(
            e['politica'], e['config'], e['episodio']))

    lineas = ['# Métricas del protocolo (anexo B.4)', '',
              'Banda objetivo {:.2f}-{:.2f} m · desviación < {:.0f}° · '
              'colisión < {:.2f} m · perdido > {:.2f} m o {:.0f} s sin ver · '
              'episodios de {:.0f} s'.format(
                  cfg['banda_min_m'], cfg['banda_max_m'],
                  cfg['desv_max_grados'], cfg['sep_colision_m'],
                  cfg['sep_perdido_m'], cfg['eval_sin_ver_s'],
                  cfg['eval_duracion_s']), '']

    for politica in sorted({e['politica'] for e in episodios}):
        de_pol = [e for e in episodios if e['politica'] == politica]
        lineas += ['## Política: ' + politica, '',
                   '| Config. | Episodios | Completados | Colisión | '
                   'Guía perdido | Otra causa | % pasos en banda | '
                   'Separación media (m) | Desviación media (°) | '
                   '% pasos < {:.0f}° |'.format(cfg['desv_max_grados']),
                   '|---|---|---|---|---|---|---|---|---|---|']
        grupos = [(c.upper(), [e for e in de_pol if e['config'] == c])
                  for c in CONFIGS] + [('**Total**', de_pol)]
        for etiqueta, grupo in grupos:
            if not grupo:
                continue
            m = calcular_metricas(grupo, cfg)
            d = m['desenlaces']
            lineas.append(
                '| {} | {} | {} ({:.0f} %) | {} | {} | {} | {:.1f} | {:.3f} | '
                '{:.1f} | {:.1f} |'.format(
                    etiqueta, m['n'], m['completados'], m['pct_completados'],
                    d['colisión'], d['guía perdido'], d['otra causa'],
                    m['pct_banda'], m['sep_media'], m['desv_media'],
                    m['pct_desv']))
        lineas.append('')

    texto = '\n'.join(lineas)
    print(texto)
    with open(os.path.join(RUTA_EVAL, 'metricas.md'), 'w') as f:
        f.write(texto + '\n')
    print('Guardado en {}'.format(os.path.join(RUTA_EVAL, 'metricas.md')))


def main():
    p = argparse.ArgumentParser(
        description='Evaluador con el protocolo del anexo B.')
    modo = p.add_mutually_exclusive_group()
    modo.add_argument('--aleatorio', action='store_true',
                      help='línea base: política aleatoria')
    modo.add_argument('--metricas', action='store_true',
                      help='calcula las tablas a partir de p1_eval/')
    p.add_argument('--config', choices=CONFIGS,
                   help='configuración del guía puesta en el simulador')
    p.add_argument('--algoritmo', choices=['sac', 'ppo'], default='sac')
    p.add_argument('--etiqueta', default=None,
                   help='modelo p1_modelo_<alg>_<etiqueta>.zip')
    p.add_argument('--modelo', default=None,
                   help='ruta del modelo (sustituye a --etiqueta)')
    p.add_argument('--config-json', default=None,
                   help='valores de la configuración (p. ej. config_c1.json); '
                        'sólo si el modelo no tiene su copia .json')
    p.add_argument('--episodios', type=int, default=1,
                   help='ejecuciones de 120 s en esta configuración')
    p.add_argument('--detalle', action='store_true',
                   help='imprime una línea por paso')
    args = p.parse_args()

    if args.metricas:
        modo_metricas(args)
    else:
        if args.config is None:
            p.error('--config es obligatorio para evaluar')
        modo_ejecutar(args)


if __name__ == '__main__':
    main()
