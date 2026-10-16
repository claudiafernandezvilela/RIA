#!/usr/bin/env python3
"""
Práctica 1 — Entrenamiento y evaluación: seguimiento del vehículo guía
en "Follow City". Basado en el p1_entrenar.py de ejemplo.

Utiliza Stable-Baselines3 sobre el entorno de p1_robobo_env.py.

--------------------------------------------------------------------
USO (primera implementación: guía a velocidad constante)
--------------------------------------------------------------------

  0. En RoboboSim: mundo "Follow City", guía en modo crucero con
     velocidad mínima = máxima (p. ej. 10 y 10). Si al empezar el
     seguidor no ve la pelota porque está subiendo el TILT, reiniciar el
     simulador antes de entrenar.

     Puente (otra terminal):
         ros2 run robobo_ros2 robobo_container --ros-args \\
              -p ip:=host.docker.internal -p modules:="['blob','sim']"

  1. Calibrar el blob y ajustar p1_config.json:
         python3 p1_entrenar.py --calibrar

  2. Comprobar la interfaz de Gymnasium:
         python3 p1_entrenar.py --comprobar

  3. Línea base (política aleatoria):
         python3 p1_entrenar.py --aleatorio --episodios 5

  4. Entrenar:
         python3 p1_entrenar.py --entrenar --algoritmo sac --pasos 10000

  5. Evaluar la política aprendida (determinista):
         python3 p1_entrenar.py --evaluar --episodios 10

Los episodios se registran en p1_logs/monitor_<alg>.monitor.csv (una
fila por episodio), para hacer después las curvas de aprendizaje con
Matplotlib (apartado 9.1).

Con --config-json config_c1.json se aplican sobre config.json los
valores propios de esa configuración del guía. Al guardar el modelo se
guarda también p1_modelo_<...>.json con la configuración completa usada,
que es la que se carga después al evaluarlo.

Con --etiqueta (p. ej. --etiqueta c3) el modelo y el monitor se guardan
como p1_modelo_<alg>_<etiqueta>.zip y p1_logs/monitor_<alg>_<etiqueta>,
para no sobrescribir los de otra configuración del guía. Sin --etiqueta
se usan los nombres de siempre.
"""

import argparse
import json
import os
import time

import numpy as np

from env import RoboboSeguirEnv, calibrar, cargar_config


RUTA_MODELO = 'p1_modelo'
RUTA_LOGS = 'p1_logs'


HIPER_SAC = dict(
    learning_rate=3e-4,
    buffer_size=50_000,
    learning_starts=500,
    batch_size=256,
    tau=0.005,
    gamma=0.99,
    train_freq=1,
    gradient_steps=1,
)

HIPER_PPO = dict(
    learning_rate=3e-4,
    n_steps=512,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    gradient_steps=2,
    ent_coef='auto_0.1',
)


def construir_algoritmo(nombre, env, semilla=None):
    from stable_baselines3 import PPO, SAC

    if nombre == 'sac':
        return SAC('MlpPolicy', env, verbose=1, seed=semilla,
                   tensorboard_log=RUTA_LOGS, **HIPER_SAC)
    if nombre == 'ppo':
        return PPO('MlpPolicy', env, verbose=1, seed=semilla,
                   tensorboard_log=RUTA_LOGS, **HIPER_PPO)
    raise ValueError('Algoritmo desconocido: ' + nombre)


def config_de_modelo(ruta):
    """Ruta de la copia de la configuración guardada junto a un modelo."""
    return ruta + '.json'


def guardar_config(ruta, cfg):
    with open(config_de_modelo(ruta), 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def cargar_algoritmo(nombre, ruta, env):
    from stable_baselines3 import PPO, SAC

    clase = SAC if nombre == 'sac' else PPO
    return clase.load(ruta, env=env)


def nombre_con_etiqueta(prefijo, args):
    """prefijo_<alg>, o prefijo_<alg>_<etiqueta> si se pasó --etiqueta.
    Sirve para guardar modelo y monitor de cada configuración del guía
    (c1, c2, c3...) sin sobrescribir los de las demás."""
    nombre = prefijo + '_' + args.algoritmo
    if args.etiqueta:
        nombre += '_' + args.etiqueta
    return nombre



def modo_comprobar(args):
    from stable_baselines3.common.env_checker import check_env

    env = crear_env(args)
    try:
        check_env(env, warn=True)
        print('\nEl entorno cumple la interfaz de Gymnasium.')
    finally:
        env.close()


def modo_aleatorio(args):
    env = crear_env(args)
    try:
        resumen(env, politica=None, episodios=args.episodios,
                titulo='POLÍTICA ALEATORIA')
    finally:
        env.close()


def modo_entrenar(args):
    # Se lee una sola vez: la copia que se guarda con el modelo es la
    # configuración con la que realmente se ha entrenado, aunque los JSON
    # se editen mientras tanto.
    cfg = crear_config(args)
    env = crear_env(args, cfg)
    try:
        from stable_baselines3.common.monitor import Monitor
        os.makedirs(RUTA_LOGS, exist_ok=True)
        # Monitor escribe un CSV con una fila por episodio (recompensa,
        # longitud, tiempo) y además las causas de fin indicadas.
        env = Monitor(env,
                      filename=os.path.join(RUTA_LOGS,
                                            nombre_con_etiqueta('monitor', args)),
                      info_keywords=('choque', 'perdido', 'atascado'))

        modelo = construir_algoritmo(args.algoritmo, env, args.semilla)

        print('\nEntrenando {} durante {} pasos.'
              .format(args.algoritmo.upper(), args.pasos))
        print('Se puede interrumpir con Ctrl-C: el modelo se guarda igual.\n')

        t0 = time.time()
        try:
            modelo.learn(total_timesteps=args.pasos, progress_bar=False)
        except KeyboardInterrupt:
            print('\nEntrenamiento interrumpido por el usuario.')

        ruta = nombre_con_etiqueta(RUTA_MODELO, args)
        modelo.save(ruta)
        # Copia de la configuración con la que se ha entrenado: al evaluar
        # se usa ésta y no la de config.json, que puede haber cambiado.
        guardar_config(ruta, cfg)
        print('Configuración guardada en {}'.format(config_de_modelo(ruta)))
        dt = time.time() - t0
        print('\nModelo guardado en {}.zip'.format(ruta))
        print('Tiempo empleado: {:.1f} min'.format(dt / 60.0))
        if modelo.num_timesteps:
            print('Segundos por paso: {:.3f}'.format(dt / modelo.num_timesteps))
    finally:
        env.close()


def modo_evaluar(args):
    ruta = nombre_con_etiqueta(RUTA_MODELO, args)
    if not os.path.exists(ruta + '.zip'):
        raise SystemExit(
            'No existe {}.zip. Hay que entrenar primero.'.format(ruta))
    cfg = None
    if os.path.exists(config_de_modelo(ruta)):
        cfg = cargar_config(config_de_modelo(ruta))
        print('Configuración del modelo: {}'.format(config_de_modelo(ruta)))
    env = crear_env(args, cfg)
    try:

        modelo = cargar_algoritmo(args.algoritmo, ruta, env)
        resumen(env,
                politica=lambda obs: modelo.predict(obs, deterministic=True)[0],
                episodios=args.episodios,
                titulo='POLÍTICA APRENDIDA ({})'.format(args.algoritmo.upper()))
    finally:
        env.close()


def resumen(env, politica, episodios, titulo):
    recompensas = []
    longitudes = []
    visibles = []
    choques = perdidos = atascos = completos = 0

    print('\n' + titulo)
    print('-' * len(titulo))

    for ep in range(episodios):
        obs, _ = env.reset()
        total = 0.0
        pasos = 0
        n_visible = 0
        info = {}
        terminado = truncado = False

        while not (terminado or truncado):
            accion = (env.action_space.sample() if politica is None
                      else politica(obs))
            obs, r, terminado, truncado, info = env.step(accion)
            total += r
            pasos += 1
            n_visible += int(info.get('visible', False))

        recompensas.append(total)
        longitudes.append(pasos)
        visibles.append(n_visible / max(pasos, 1))
        if info.get('choque'):
            choques += 1
            desenlace = 'choque'
        elif info.get('atascado'):
            atascos += 1
            desenlace = 'atasco (choque con el entorno)'
        elif info.get('perdido'):
            perdidos += 1
            desenlace = 'guía perdido'
        else:
            completos += 1
            desenlace = 'tiempo agotado'

        print('episodio {:2d}   pasos {:3d}   recompensa {:8.2f}   '
              'visible {:5.1f}%   {}'
              .format(ep + 1, pasos, total, 100 * visibles[-1], desenlace))

    print('\nrecompensa media  {:.2f}  (desviación {:.2f})'
          .format(float(np.mean(recompensas)), float(np.std(recompensas))))
    print('longitud media    {:.1f} pasos'.format(float(np.mean(longitudes))))
    print('visible medio     {:.1f}%'.format(100 * float(np.mean(visibles))))
    print('sin fallo         {}/{}'.format(completos, episodios))
    print('guía perdido      {}/{}'.format(perdidos, episodios))
    print('choques           {}/{}'.format(choques, episodios))
    print('atascos           {}/{}'.format(atascos, episodios))


def crear_config(args):
    """config.json con los valores de --config-json aplicados encima."""
    return cargar_config(extra=args.config_json)


def crear_env(args, cfg=None):
    return RoboboSeguirEnv(
        pasos_max=args.pasos_max,
        usar_simulador=not args.sin_simulador,
        verbose=args.detalle,
        config=cfg if cfg is not None else crear_config(args))


def main():
    p = argparse.ArgumentParser(
        description='Práctica 1 de RIA: seguimiento de un vehículo en la '
                    'ciudad con aprendizaje por refuerzo continuo.')

    modo = p.add_mutually_exclusive_group(required=True)
    modo.add_argument('--calibrar', action='store_true',
                      help='imprime el blob verde detectado')
    modo.add_argument('--comprobar', action='store_true',
                      help='verifica la interfaz del entorno')
    modo.add_argument('--aleatorio', action='store_true',
                      help='ejecuta episodios con acciones aleatorias')
    modo.add_argument('--entrenar', action='store_true')
    modo.add_argument('--evaluar', action='store_true')

    p.add_argument('--algoritmo', choices=['sac', 'ppo'], default='sac')
    p.add_argument('--pasos', type=int, default=10_000,
                   help='pasos totales de entrenamiento')
    p.add_argument('--semilla', type=int, default=None)
    p.add_argument('--episodios', type=int, default=5)
    p.add_argument('--pasos-max', type=int, default=200,
                   help='longitud máxima de un episodio')
    p.add_argument('--sin-simulador', action='store_true',
                   help='no usar el módulo sim; reinicio a mano')
    p.add_argument('--detalle', action='store_true',
                   help='imprime una línea por paso')
    p.add_argument('--etiqueta', default=None,
                   help='sufijo del modelo y del monitor (c1, c2, c3...); '
                        'sin él se usan los nombres de siempre')

    p.add_argument('--config-json', default=None,
                   help='valores propios de una configuración del guía '
                        '(p. ej. config_c1.json), aplicados sobre config.json')

    args = p.parse_args()

    if args.calibrar:
        calibrar()
    elif args.comprobar:
        modo_comprobar(args)
    elif args.aleatorio:
        modo_aleatorio(args)
    elif args.entrenar:
        modo_entrenar(args)
    elif args.evaluar:
        modo_evaluar(args)


if __name__ == '__main__':
    main()