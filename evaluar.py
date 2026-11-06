#!/usr/bin/env python3
"""
Prácticas 1 y 2 — Evaluador con el protocolo común (anexo B del enunciado).

Ejecuta una política (la aprendida, en modo determinista, la red de un
genoma de NEAT o la aleatoria como línea base) durante episodios de 120 s y la mide con la verdad del
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

  --etiqueta elige el modelo modelos/<config>/p1_modelo_<alg>_<etiqueta>.zip
  (como en train.py); --modelo permite dar la ruta directamente. Se evalúa con la
  configuración guardada junto al modelo (p1_modelo_<...>.json); para la
  aleatoria, o un modelo sin esa copia, con --config-json:

      python3 evaluar.py --config c1 --aleatorio --config-json config_c1.json

  Práctica 2: un genoma de NEAT con --genoma. Se evalúa con la
  configuración de NEAT y del entorno de su evolución (config-p2.ini y
  entorno.json de evoluciones/<etiqueta>/). --carpeta separa los
  resultados de la P2 (incluidas las políticas de la P1 vueltas a evaluar
  para la comparación, que tiene que hacerse en la misma sesión):

      python3 evaluar.py --config c1 --carpeta p2_eval \\
              --genoma evoluciones/c1_s2/genomas/mejor_gen020.pkl
      python3 evaluar.py --config c1 --carpeta p2_eval --etiqueta c1_s1
      python3 evaluar.py --metricas --carpeta p2_eval

  Cuando estén todas las ejecuciones, las tablas de métricas:

      python3 evaluar.py --metricas

  Se generan en p1_eval/ (o en --carpeta):
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
               'separacion_m', 'desviacion_grados', 'visible', 'blob_x', 'tamano',
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
                sep, info.get('desviacion'), visible, info.get('x'), info.get('tamano'),
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


def cargar_genoma(ruta_genoma):
    """Red de NEAT de un genoma guardado en evoluciones/<etiqueta>/genomas/
    o de evoluciones/<etiqueta>/mejor_genoma.pkl.
    Devuelve (red, genoma, carpeta de la evolución): la carpeta tiene la
    configuración de NEAT (config-p2.ini) y la del entorno (entorno.json)
    con las que se evolucionó."""
    import pickle
    import neat
    # genomas/mejor_genNNN.pkl o mejor_genoma.pkl, en la carpeta de la
    # evolución: se busca config-p2.ini al lado o un nivel por encima
    carpeta = os.path.dirname(os.path.abspath(ruta_genoma))
    if not os.path.exists(os.path.join(carpeta, 'config-p2.ini')):
        carpeta = os.path.dirname(carpeta)
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         os.path.join(carpeta, 'config-p2.ini'))
    with open(ruta_genoma, 'rb') as f:
        genoma = pickle.load(f)
    return (neat.nn.FeedForwardNetwork.create(genoma, config), genoma,
            carpeta)


def modo_ejecutar(args):
    from env import RoboboSeguirEnv, cargar_config

    # Los umbrales del protocolo se toman siempre de config.json
    umbrales = {k: v for k, v in cargar_config().items()
                if k.startswith(('eval_', 'banda_', 'desv_'))}
    extra = ' + ' + args.config_json if args.config_json else ''

    ruta = None
    if args.genoma:
        # P2: la configuración del entorno de la evolución del genoma
        # (observación con la que se evolucionó y escala de la acción)
        red, genoma, carpeta = cargar_genoma(args.genoma)
        cfg = dict(cargar_config(os.path.join(carpeta, 'entorno.json'),
                                 extra=args.config_json), **umbrales)
        print('Configuración de la evolución: {}{}'.format(
            os.path.join(carpeta, 'entorno.json'), extra))
    else:
        # P1: la configuración guardada junto al modelo (la de su
        # entrenamiento), porque la escala de la acción (v_min, v_max,
        # w_max) tiene que ser la misma. Para la política aleatoria, o un
        # modelo antiguo sin copia, config.json con --config-json encima.
        from train import cargar_algoritmo, config_de_modelo, ruta_modelo
        if not args.aleatorio:
            ruta = args.modelo or ruta_modelo(args.algoritmo, args.etiqueta)
            ruta = ruta[:-4] if ruta.endswith('.zip') else ruta
            if not os.path.exists(ruta + '.zip'):
                raise SystemExit('No existe {}.zip'.format(ruta))
        if ruta and os.path.exists(config_de_modelo(ruta)):
            # --config-json se aplica encima de la copia del modelo: sirve
            # para probar un cambio que no afecta a la red (p. ej. el tilt)
            # o para la calibración del robot real.
            cfg = dict(cargar_config(config_de_modelo(ruta),
                                     extra=args.config_json), **umbrales)
            print('Configuración del modelo: {}{}'.format(
                config_de_modelo(ruta), extra))
        else:
            cfg = cargar_config(extra=args.config_json)
            if ruta:
                print('[aviso] {} no tiene copia de su configuración; se usa '
                      'config.json{}. Comprobar que v_min, v_max y w_max son '
                      'los del entrenamiento.'.format(ruta, extra))

    # El fin por pelota no vista lo decide el evaluador con el reloj
    # (3 s, anexo B.3), no el entorno en pasos: se desactiva el de éste.
    # Tampoco debe truncar por pasos antes de los 120 s.
    cfg_env = dict(cfg, pasos_perdido_max=10 ** 9)
    env = RoboboSeguirEnv(pasos_max=10 ** 9, config=cfg_env,
                          verbose=args.detalle)

    try:
        if args.genoma:
            # p. ej. p2_c1_s2_id568: evolución e id del genoma
            nombre = 'p2_{}_id{}'.format(os.path.basename(carpeta), genoma.key)
            politica = lambda obs: np.array(red.activate(obs),
                                            dtype=np.float32)
        elif args.aleatorio:
            nombre = 'aleatoria'
            politica = lambda obs: env.action_space.sample()
        else:
            modelo = cargar_algoritmo(args.algoritmo, ruta, env)
            nombre = os.path.basename(ruta)
            # Política determinista (anexo B.2)
            politica = lambda obs: modelo.predict(obs, deterministic=True)[0]

        os.makedirs(args.carpeta, exist_ok=True)
        ruta_ep = os.path.join(args.carpeta, 'episodios.csv')
        nuevo = not os.path.exists(ruta_ep)

        print('\nEvaluando {} en {} ({} episodio/s de {:.0f} s)'.format(
            nombre, args.config.upper(), args.episodios,
            cfg['eval_duracion_s']))
        # Numeración a continuación de los episodios ya registrados de esta
        # política y configuración, para no sobrescribir sus CSV de pasos.
        previos = 0
        if not nuevo:
            with open(ruta_ep) as f:
                previos = max([int(e['episodio']) for e in csv.DictReader(f)
                               if e['politica'] == nombre
                               and e['config'] == args.config] or [0])
        for ep in range(previos + 1, previos + args.episodios + 1):
            ruta_csv = os.path.join(args.carpeta, '{}_{}_ep{}.csv'.format(
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
        if not os.path.exists(e['_csv']):
            # El desenlace cuenta, pero sin registro por paso no hay
            # separación ni desviación de ese episodio.
            print('[aviso] Falta {}: el episodio cuenta en completados y '
                  'desenlaces, pero no en separación ni desviación.'
                  .format(e['_csv']))
            continue
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

    ruta_ep = os.path.join(args.carpeta, 'episodios.csv')
    if not os.path.exists(ruta_ep):
        raise SystemExit('No hay {}. Hay que evaluar primero.'.format(ruta_ep))
    with open(ruta_ep) as f:
        episodios = list(csv.DictReader(f))
    for e in episodios:
        e['_csv'] = os.path.join(args.carpeta, '{}_{}_ep{}.csv'.format(
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
    with open(os.path.join(args.carpeta, 'metricas.md'), 'w') as f:
        f.write(texto + '\n')
    print('Guardado en {}'.format(os.path.join(args.carpeta, 'metricas.md')))


def main():
    p = argparse.ArgumentParser(
        description='Evaluador con el protocolo del anexo B.')
    modo = p.add_mutually_exclusive_group()
    modo.add_argument('--aleatorio', action='store_true',
                      help='línea base: política aleatoria')
    modo.add_argument('--metricas', action='store_true',
                      help='calcula las tablas a partir de --carpeta')
    modo.add_argument('--genoma', default=None,
                      help='P2: genoma de NEAT (evoluciones/<etiqueta>/'
                           'genomas/mejor_genNNN.pkl)')
    p.add_argument('--config', choices=CONFIGS,
                   help='configuración del guía puesta en el simulador')
    p.add_argument('--algoritmo', choices=['sac', 'ppo'], default='sac')
    p.add_argument('--etiqueta', default=None,
                   help='modelo p1_modelo_<alg>_<etiqueta>.zip')
    p.add_argument('--modelo', default=None,
                   help='ruta del modelo (sustituye a --etiqueta)')
    p.add_argument('--config-json', default=None,
                   help='valores que se aplican encima de la configuración '
                        '(la copia .json del modelo, o config.json)')
    p.add_argument('--episodios', type=int, default=1,
                   help='ejecuciones de 120 s en esta configuración')
    p.add_argument('--carpeta', default=RUTA_EVAL,
                   help='carpeta de los registros y las métricas '
                        '(p1_eval; p2_eval para la P2)')
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
