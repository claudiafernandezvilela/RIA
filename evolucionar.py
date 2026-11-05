#!/usr/bin/env python3
"""
Práctica 2 — Evolución del controlador del seguidor con NEAT-Python.

Cada genoma se traduce en una red que conduce al seguidor durante un
episodio del entorno de la P1 (RoboboSeguirEnv). Con los info de cada paso
se calcula su calidad (calidad.py) y NEAT selecciona, cruza y muta.

--------------------------------------------------------------------
USO
--------------------------------------------------------------------

  0. RoboboSim con "Follow City" y el guía en la configuración que se va a
     evolucionar (p. ej. C2: crucero, 10-40). El guía se configura A MANO en
     el simulador: el script no lo cambia, sólo lo anota (--guia).

     Puente (otra terminal):
         ros2 run robobo_ros2 robobo_container --ros-args \\
              -p ip:=host.docker.internal -p modules:="['blob','sim']"

  1. Evolución nueva:
         python3 evolucionar.py --etiqueta c2_s1 --guia c2 --semilla 1 \\
                                --generaciones 20

  2. Si se corta (puente colgado, Ctrl-C...): relanzar el puente y
         python3 evolucionar.py --etiqueta c2_s1 --guia c2 --reanudar \\
                                --generaciones 20

     Para la evolución incremental se reanuda con otra configuración del
     guía puesta en el simulador (--guia c3) y, si hace falta, otra duración
     (--pasos-max). --generaciones es el total, no las que faltan.

--------------------------------------------------------------------
RESULTADOS: evoluciones/<etiqueta>/
--------------------------------------------------------------------

  config-p2.ini      copia de la configuración de NEAT, con la semilla usada
  entorno.json       configuración completa del entorno (observación, acción,
                     calibración y fin de episodio)
  evolucion.csv      una fila por generación (datos de las figuras y coste)
  chk/p2-N           punto de control: población lista para la generación N
  genomas/           mejor genoma de cada generación
  mejor_genoma.pkl   mejor genoma de toda la evolución (al terminar)
"""

import argparse
import csv
import glob
import json
import os
import pickle
import re
import statistics
import time

import numpy as np
import neat

from calidad import calidad, sin_arranque
from env import RoboboSeguirEnv, cargar_config

DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG_NEAT = os.path.join(DIR, 'config-p2.ini')
RUTA_EVOLUCIONES = os.path.join(DIR, 'evoluciones')

# Pasos del entorno y episodios evaluados en este proceso. Los actualiza
# evaluar_genoma() y los lee RegistroGeneracion para el coste.
CONTADOR = {'pasos': 0, 'evaluaciones': 0}


class RegistroGeneracion(neat.reporting.BaseReporter):
    """Escribe una fila por generación en un CSV y guarda el mejor genoma de
    cada generación (indicaciones técnicas, apartado 6.2, con dos columnas
    más: la configuración del guía y la duración del episodio, que cambian
    en la evolución incremental, y el tamaño de cada especie, para la figura
    de especiación aunque la evolución se haya reanudado).

    Al reanudar continúa los contadores de evaluaciones, pasos y segundos
    desde la última fila. No guarda archivos abiertos ni el entorno: el
    Checkpointer serializa los registros con pickle."""

    CAMPOS = ['generacion', 'guia', 'pasos_max', 'cal_mejor', 'cal_media',
              'cal_desv', 'especies', 'tam_especies', 'nodos_mejor',
              'conexiones_mejor', 'evaluaciones', 'pasos', 'segundos']

    def __init__(self, ruta_csv, carpeta_genomas, guia, pasos_max):
        self.ruta, self.carpeta = ruta_csv, carpeta_genomas
        self.guia, self.pasos_max = guia, pasos_max
        os.makedirs(carpeta_genomas, exist_ok=True)
        self.base = {'evaluaciones': 0, 'pasos': 0, 'segundos': 0.0}
        if os.path.exists(ruta_csv):              # se reanuda una evolución
            with open(ruta_csv) as f:
                filas = list(csv.DictReader(f))
            if filas:
                self.base = {k: float(filas[-1][k]) for k in self.base}
        else:
            with open(ruta_csv, 'w', newline='') as f:
                csv.writer(f).writerow(self.CAMPOS)
        self.inicio = dict(CONTADOR)
        self.t0, self.gen = time.time(), 0

    def start_generation(self, generation):
        self.gen = generation

    def post_evaluate(self, config, population, species, best_genome):
        cal = [g.fitness for g in population.values()]
        nodos, conexiones = best_genome.size()
        tam = ';'.join('{}:{}'.format(sid, len(s.members))
                       for sid, s in sorted(species.species.items()))
        fila = [self.gen, self.guia, self.pasos_max,
                round(best_genome.fitness, 3),
                round(statistics.mean(cal), 3),
                round(statistics.pstdev(cal), 3),
                len(species.species), tam, nodos, conexiones,
                int(self.base['evaluaciones'] + CONTADOR['evaluaciones']
                    - self.inicio['evaluaciones']),
                int(self.base['pasos'] + CONTADOR['pasos']
                    - self.inicio['pasos']),
                round(self.base['segundos'] + time.time() - self.t0, 1)]
        with open(self.ruta, 'a', newline='') as f:
            csv.writer(f).writerow(fila)
        ruta = os.path.join(self.carpeta, 'mejor_gen{:03d}.pkl'.format(self.gen))
        with open(ruta, 'wb') as f:
            pickle.dump(best_genome, f)


def reinicio_fallido(registro):
    """El robot sale a unos 0,6 m del guía y en un paso (0,4 s) no puede
    alejarse hasta 0,90 m: si el episodio acaba perdido en el primer paso,
    la escena no se ha reiniciado (robot atrapado contra una señal, reset
    que no ha llegado al simulador...)."""
    return len(registro) == 1 and bool(registro[0].get('perdido'))


def evaluar_genoma(env, red, n_max, intentos=3):
    """Un episodio con la red como controlador. Devuelve el registro de
    info de cada paso (lo que necesita la calidad). Si el reinicio falla se
    repite el episodio; si falla `intentos` veces seguidas se lanza
    RuntimeError para detener la evolución sin asignar calidades falsas."""
    for _ in range(intentos):
        registro = _episodio(env, red, n_max)
        if not reinicio_fallido(registro):
            return registro
        print('  (reinicio fallido: el episodio acaba perdido en el primer '
              'paso; se repite)', flush=True)
    raise RuntimeError(
        'El simulador no se reinicia (episodio perdido en el primer paso {} '
        'veces seguidas). Reinicia la escena en RoboboSim y reanuda.'.format(
            intentos))


def _episodio(env, red, n_max):
    obs, _ = env.reset()
    registro = []
    for _ in range(n_max):
        accion = np.array(red.activate(obs), dtype=np.float32)
        obs, _, terminado, truncado, info = env.step(accion)
        registro.append(info)
        if terminado or truncado or sin_arranque(registro) is not None:
            break
    CONTADOR['pasos'] += len(registro)
    CONTADOR['evaluaciones'] += 1
    return registro


def desenlace(registro):
    """Causa de fin del episodio, para mostrarla por consola."""
    if not registro:
        return '-'
    if sin_arranque(registro) is not None:
        return 'quieto'
    ultimo = registro[-1]
    for clave in ('choque', 'atascado', 'perdido'):
        if ultimo.get(clave):
            return clave
    return 'completo'


def hacer_eval_genomes(env, n_max):
    """Función de evaluación que se pasa a Population.run(). Si falla la
    comunicación (el entorno lanza RuntimeError) o falta la separación real
    (calidad lanza ValueError), la excepción se deja subir: no se asigna
    calidad 0 a un individuo por un fallo de la infraestructura
    (indicaciones, 6.1). La evolución se reanuda desde el último punto de
    control."""
    def eval_genomes(genomas, config):
        for i, (gid, genoma) in enumerate(genomas, 1):
            t0 = time.time()
            red = neat.nn.FeedForwardNetwork.create(genoma, config)
            registro = evaluar_genoma(env, red, n_max)
            genoma.fitness = calidad(registro, n_max)
            print('  individuo {:2d}/{}  id {:5d}  calidad {:6.1f}  '
                  'pasos {:3d}/{}  {:9s} {:5.1f} s'.format(
                      i, len(genomas), gid, genoma.fitness, len(registro),
                      n_max, desenlace(registro), time.time() - t0),
                  flush=True)
    return eval_genomes


def ultimo_checkpoint(carpeta_chk):
    """Ruta del punto de control de número más alto, o None."""
    rutas = glob.glob(os.path.join(carpeta_chk, 'p2-*'))
    if not rutas:
        return None
    return max(rutas, key=lambda r: int(r.rsplit('-', 1)[1]))


def recortar_csv(ruta_csv, generacion):
    """Al reanudar desde el punto de control de la generación N, borra las
    filas de la generación N en adelante: si el proceso se cortó después de
    escribir la fila y antes de guardar el punto de control, esa generación
    se vuelve a evaluar y quedaría repetida."""
    if not os.path.exists(ruta_csv):
        return
    with open(ruta_csv) as f:
        filas = list(csv.reader(f))
    cabecera, datos = filas[0], filas[1:]
    datos = [d for d in datos if int(d[0]) < generacion]
    with open(ruta_csv, 'w', newline='') as f:
        csv.writer(f).writerows([cabecera] + datos)


def preparar_carpeta(args, carpeta):
    """Evolución nueva: crea la carpeta con la copia de la configuración de
    NEAT (con la semilla de --semilla) y la del entorno."""
    if os.path.exists(os.path.join(carpeta, 'evolucion.csv')):
        raise SystemExit(
            'Ya existe la evolución {}. Usa --reanudar para continuarla u '
            'otra --etiqueta para empezar una nueva.'.format(carpeta))
    os.makedirs(os.path.join(carpeta, 'chk'), exist_ok=True)

    with open(RUTA_CONFIG_NEAT) as f:
        texto = f.read()
    texto = re.sub(r'(?m)^seed\s*=.*$', 'seed = {}'.format(args.semilla), texto)
    with open(os.path.join(carpeta, 'config-p2.ini'), 'w') as f:
        f.write(texto)

    cfg = cargar_config(extra=os.path.join(DIR, args.config_json))
    with open(os.path.join(carpeta, 'entorno.json'), 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser(
        description='Práctica 2 de RIA: evolución del seguidor con NEAT.')
    p.add_argument('--etiqueta', required=True,
                   help='nombre de la evolución (p. ej. c2_s1); carpeta '
                        'evoluciones/<etiqueta>/')
    p.add_argument('--guia', required=True, choices=['c1', 'c2', 'c3', 'c4'],
                   help='configuración del guía puesta en el simulador '
                        '(sólo se anota en el CSV)')
    p.add_argument('--semilla', type=int, default=1,
                   help='semilla de NEAT (evolución nueva)')
    p.add_argument('--generaciones', type=int, default=20,
                   help='número TOTAL de generaciones de la evolución')
    p.add_argument('--pasos-max', type=int, default=None,
                   help='duración máxima del episodio en pasos de ~0,4 s '
                        '(125 = 50 s, por defecto); al reanudar, por defecto '
                        'la de la última generación')
    p.add_argument('--config-json', default='config_c3.json',
                   help='valores aplicados sobre config.json (observación '
                        'de 6 entradas, tilt 100); sólo en evolución nueva')
    p.add_argument('--reanudar', action='store_true',
                   help='continuar desde el último punto de control')
    args = p.parse_args()

    carpeta = os.path.join(RUTA_EVOLUCIONES, args.etiqueta)
    carpeta_chk = os.path.join(carpeta, 'chk')
    ruta_csv = os.path.join(carpeta, 'evolucion.csv')

    if args.reanudar:
        chk = ultimo_checkpoint(carpeta_chk)
        if chk is None:
            raise SystemExit('No hay puntos de control en ' + carpeta_chk)
        # El punto de control guarda su propia configuración de NEAT
        poblacion = neat.Checkpointer.restore_checkpoint(chk)
        recortar_csv(ruta_csv, poblacion.generation)
        if args.pasos_max is None:
            with open(ruta_csv) as f:
                filas = list(csv.DictReader(f))
            args.pasos_max = int(filas[-1]['pasos_max']) if filas else 125
        print('Reanudando {} desde {} (generación {})'.format(
            args.etiqueta, os.path.basename(chk), poblacion.generation))
    else:
        if args.pasos_max is None:
            args.pasos_max = 125
        preparar_carpeta(args, carpeta)
        config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                             neat.DefaultSpeciesSet, neat.DefaultStagnation,
                             os.path.join(carpeta, 'config-p2.ini'))
        poblacion = neat.Population(config)
        print('Evolución nueva {} (semilla {})'.format(
            args.etiqueta, args.semilla))

    faltan = args.generaciones - poblacion.generation
    if faltan <= 0:
        raise SystemExit('La evolución ya tiene {} generaciones. Sube '
                         '--generaciones para continuarla.'.format(
                             poblacion.generation))

    # La configuración del entorno es siempre la copia de la carpeta: la
    # misma observación y calibración en toda la evolución
    cfg = cargar_config(os.path.join(carpeta, 'entorno.json'))
    if poblacion.config.genome_config.num_inputs != (6 if cfg.get('obs_delta') else 5):
        raise SystemExit('num_inputs de config-p2.ini no coincide con la '
                         'observación del entorno.')

    # Los registros no se guardan en el punto de control: se añaden siempre
    poblacion.add_reporter(neat.StdOutReporter(True))
    poblacion.add_reporter(neat.Checkpointer(
        generation_interval=1,
        filename_prefix=os.path.join(carpeta_chk, 'p2-')))
    poblacion.add_reporter(RegistroGeneracion(
        ruta_csv, os.path.join(carpeta, 'genomas'), args.guia, args.pasos_max))

    print('Guía: {}   episodio: {} pasos   generaciones: {} -> {}\n'.format(
        args.guia, args.pasos_max, poblacion.generation, args.generaciones))

    env = RoboboSeguirEnv(pasos_max=args.pasos_max, usar_simulador=True,
                          config=cfg)
    try:
        mejor = poblacion.run(hacer_eval_genomes(env, args.pasos_max), faltan)
        with open(os.path.join(carpeta, 'mejor_genoma.pkl'), 'wb') as f:
            pickle.dump(mejor, f)
        print('\nEvolución terminada. Mejor calidad: {:.1f}'.format(mejor.fitness))
    except (RuntimeError, ValueError, KeyboardInterrupt) as e:
        print('\nEvolución detenida en la generación {}: {}'.format(
            poblacion.generation, e or 'Ctrl-C'))
        print('Para continuar (con el puente relanzado si se ha colgado):')
        print('    python3 evolucionar.py --etiqueta {} --guia {} --reanudar '
              '--generaciones {}'.format(args.etiqueta, args.guia,
                                         args.generaciones))
    finally:
        env.close()


if __name__ == '__main__':
    main()
