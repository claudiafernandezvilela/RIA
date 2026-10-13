#!/usr/bin/env python3
"""
Práctica 1 — Entorno Gymnasium "Follow City" para el Robobo en RoboboSim.

Tarea: el robot seguidor (al que se conecta el nodo puente) debe circular
detrás del vehículo guía, que lleva una pelota verde, manteniendo la
separación, sin chocar y sin perderlo de vista.

Primera implementación (semana 1): el guía circula a VELOCIDAD CONSTANTE
(se configura en el simulador, p. ej. modo crucero con mínimo = máximo).

Basado en el ejemplo RoboboParedEnv (p1_robobo_env.py original) y en los
espacios definidos en espacios.txt.

--------------------------------------------------------------------
REQUISITOS
--------------------------------------------------------------------

1. RoboboSim en ejecución en el anfitrión, con el mundo "Follow City".

2. Nodo puente del seguidor, SOLO con los módulos necesarios (anexo A):

       ros2 run robobo_ros2 robobo_container --ros-args \\
            -p ip:=host.docker.internal -p modules:="['blob','sim']"

--------------------------------------------------------------------
SOBRE LOS TIPOS DE MENSAJE
--------------------------------------------------------------------

Los tipos de color_blobs, set_active_color_blobs, reset_simulation y
robot_location NO se escriben a mano: se consultan al grafo de ROS 2
(equivalente a `ros2 topic type` / `ros2 service type`) y se importan
dinámicamente. Así no dependemos de adivinar el nombre exacto del tipo.
Si algo falla, comprobar a mano:

    ros2 topic info /robobo/robot_0/smartphone/color_blobs
    ros2 interface show <tipo que salga>

--------------------------------------------------------------------
CALIBRACIÓN
--------------------------------------------------------------------

Todos los parámetros dependientes de la calibración están en
p1_config.json (requisito del enunciado, apartado 7). Antes de entrenar:

    python3 p1_entrenar.py --calibrar

y ajustar blob_x_max, s_max, s_objetivo, s_cerca y s_choque.
"""

import json
import os
import time
from collections import deque

import numpy as np

import gymnasium as gym
from gymnasium import spaces

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from rosidl_runtime_py.utilities import get_message, get_service



RUTA_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'config.json')


def cargar_config(ruta=RUTA_CONFIG):
    with open(ruta) as f:
        return json.load(f)


def _esperar_tipo(nodo, nombre, servicio=False, espera_s=5.0):
    """Devuelve la cadena de tipo (p. ej. 'pkg/msg/Tipo') de un tópico o
    servicio, consultando el grafo de ROS 2. None si no aparece."""
    t0 = time.time()
    while time.time() - t0 < espera_s:
        lista = (nodo.get_service_names_and_types() if servicio
                 else nodo.get_topic_names_and_types())
        for n, tipos in lista:
            if n == nombre and tipos:
                return tipos[0]
        rclpy.spin_once(nodo, timeout_sec=0.1)
    return None


def _campo(obj, *nombres, defecto=None):
    """Lee el primer atributo que exista entre varios nombres posibles."""
    for n in nombres:
        if hasattr(obj, n):
            return getattr(obj, n)
    return defecto


def _lista_blobs(msg):
    """Extrae la lista de blobs de un mensaje BlobArray."""
    lista = _campo(msg, 'blobs', 'blob_array', 'data', defecto=None)
    if lista is None:
        # Último recurso: el primer campo que sea una secuencia
        for nombre in msg.get_fields_and_field_types():
            valor = getattr(msg, nombre)
            if isinstance(valor, (list, tuple)):
                return list(valor)
        return []
    return list(lista)


def _blob_de_color(msg, color, size_min=0.0):
    """Devuelve (x, y, size) del blob del color pedido, o None.

    El detector publica una entrada por cada color activo AUNQUE no lo vea:
    en ese caso llega con x = 0, y = 0 y size = 0. Por eso la pelota sólo
    se considera visible si size > size_min (comprobado con --aleatorio:
    con el criterio "hay entrada verde" salía siempre visible = 1)."""
    for b in _lista_blobs(msg):
        c = str(_campo(b, 'color', defecto='')).lower()
        if c == color:
            x = float(_campo(b, 'x', 'pos_x', 'posx', defecto=0.0))
            y = float(_campo(b, 'y', 'pos_y', 'posy', defecto=0.0))
            s = float(_campo(b, 'size', 'area', defecto=0.0))
            if s <= size_min:
                return None
            return x, y, s
    return None


class RoboboSeguirEnv(gym.Env):
    """Seguimiento del vehículo guía en la ciudad de RoboboSim.

    Observación (Box, float32, dimensión 5) — según espacios.txt
        [0]  visible: 1 si el detector ve el blob verde, 0 si no
        [1]  x del blob, centrada y normalizada, en [-1, 1]
        [2]  tamaño del blob / S_max, recortado, en [0, 1]
        [3]  velocidad lineal ordenada en el paso anterior, en [-1, 1]
        [4]  velocidad angular ordenada en el paso anterior, en [-1, 1]

        Cuando la pelota no se ve: visible = 0 y tamaño = 0; se conserva
        la última x, que indica hacia qué lado se perdió.

        Toda la observación procede de sensores del seguidor por ROS 2
        (blobs + órdenes propias). Nada del módulo sim (apartado 4).

    Acción (Box, float32, dimensión 2)
        [0]  velocidad lineal, en [-1, 1], reescalada a [V_MIN, V_MAX]
        [1]  velocidad angular, en [-1, 1], reescalada a [-W_MAX, W_MAX]
        Se publica como Twist en base/cmd_vel.

    Recompensa — en _recompensa(), con los cuatro términos de espacios.txt.

    Fin de episodio (espacios.txt, "Reinicio aprendizaje")
        terminated: con simulador, criterios del anexo B con la separación
                    real (colisión < sep_colision_m; guía perdido si
                    separación > sep_perdido_m o pelota sin ver durante
                    pasos_perdido_max pasos); sin simulador, aproximación por
                    el tamaño del blob. Además, atasco (choque con el
                    entorno, detectado con la pose del simulador).
                    (no visible, o visible pero más pequeño que s_lejos)
        truncated:  tiempo máximo del episodio (pasos_max)
    """

    metadata = {'render_modes': []}

    def __init__(self, pasos_max=200, usar_simulador=True,
                 verbose=False, config=None):
        super().__init__()

        self.cfg = config if config is not None else cargar_config()
        c = self.cfg
        self.pasos_max = pasos_max
        self.verbose = verbose
        self.color = c['blob_color']

        # -------------------------------------------------- ROS 2
        if not rclpy.ok():
            rclpy.init()
        self.nodo = Node('p1_entorno_seguir')

        self.pub_vel = self.nodo.create_publisher(
            Twist, c['ns_base'] + '/cmd_vel', 10)

        # Blobs de color: canal de percepción (5 Hz, se publica también vacío)
        topico_blobs = c['ns_smartphone'] + '/color_blobs'
        tipo = _esperar_tipo(self.nodo, topico_blobs)
        if tipo is None:
            raise RuntimeError(
                'No aparece el tópico {}. ¿Está el puente lanzado con el '
                "módulo 'blob'?".format(topico_blobs))
        self._blob = None        # (x, y, size) o None si no se ve
        self._n_blobs = 0        # mensajes recibidos (vacíos incluidos)
        self.nodo.create_subscription(
            get_message(tipo), topico_blobs, self._cb_blobs, 1)

        self._activar_solo_color()

        # Inclinación de la cámara (servicio base/move_tilt: angle, speed).
        # Se fija al arrancar y tras cada reinicio de escena, que la
        # devuelve a su posición por defecto. null en el JSON = no tocarla.
        self._cli_tilt = None
        if c.get('tilt_angulo') is not None:
            nombre = c['ns_base'] + '/move_tilt'
            tipo = _esperar_tipo(self.nodo, nombre, servicio=True, espera_s=3.0)
            if tipo is None:
                print('[aviso] No aparece {}; no se fija el tilt.'.format(nombre))
            else:
                self._srv_tilt = get_service(tipo)
                self._cli_tilt = self.nodo.create_client(self._srv_tilt, nombre)
                self._fijar_tilt()

        # -------------------------------------------------- simulador
        # Canal privilegiado: reinicio de la escena y pose del seguidor
        # (esta última sólo para registro).
        self.usar_simulador = usar_simulador
        self._cli_reset = None
        self._sim_lib = None
        self._pose = None
        if usar_simulador:
            self._preparar_reset()
            self._suscribir_pose(c['ns_sim'] + '/robot_location', '_pose')

        # Pose del guía (objeto del simulador, no un robot: el módulo sim
        # del puente no la publica). Se lee con la biblioteca robobosim.
        self._sim_guia = None
        if usar_simulador:
            try:
                from robobosim.RoboboSim import RoboboSim
                self._sim_guia = RoboboSim(c['sim_ip'])
                self._sim_guia.connect()
                time.sleep(1.0)
                if self._sim_guia.getObjectLocation(c['guia_objeto']) is None:
                    print('[aviso] No se encuentra el objeto {} en el '
                          'simulador; no se mide la separación real.'
                          .format(c['guia_objeto']))
                    self._sim_guia.disconnect()
                    self._sim_guia = None
            except Exception as e:
                print('[aviso] No se puede leer la pose del guía ({}); no se '
                      'mide la separación real.'.format(e))
                self._sim_guia = None

        # -------------------------------------------------- espacios
        #          visible    x     tamaño   v     w
        low = [0.0, -1.0, 0.0, -1.0, -1.0]
        high = [1.0, 1.0, 1.0, 1.0, 1.0]
        self.observation_space = spaces.Box(
            low=np.array(low, dtype=np.float32),
            high=np.array(high, dtype=np.float32), dtype=np.float32)

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # -------------------------------------------------- estado
        self.pasos = 0
        self.pasos_perdido = 0
        self.ultima_accion = np.zeros(2, dtype=np.float32)
        self._ultima_x = 0.0
        # Poses recientes del seguidor (sólo para detectar atascos)
        self._poses_recientes = deque(maxlen=c['atasco_pasos'] + 1)

        self._esperar_lectura_nueva(inicial=True)



    def _cb_blobs(self, msg):
        """Se ejecuta dentro de spin_once. Guarda el blob verde (o None)."""
        self._blob = _blob_de_color(msg, self.color,
                                    self.cfg['blob_size_min'])
        self._n_blobs += 1

    def _activar_solo_color(self):
        """Activa sólo la detección del color del guía (servicio
        smartphone/set_active_color_blobs: red, green, blue, custom)."""
        nombre = self.cfg['ns_smartphone'] + '/set_active_color_blobs'
        tipo = _esperar_tipo(self.nodo, nombre, servicio=True, espera_s=3.0)
        if tipo is None:
            print('[aviso] No se encuentra {}; se usan los colores activos '
                  'por defecto.'.format(nombre))
            return
        srv = get_service(tipo)
        cli = self.nodo.create_client(srv, nombre)
        if not cli.wait_for_service(timeout_sec=3.0):
            print('[aviso] {} no responde.'.format(nombre))
            return
        req = srv.Request()
        for col in ('red', 'green', 'blue', 'custom'):
            if hasattr(req, col):
                setattr(req, col, col == self.color)
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(self.nodo, fut, timeout_sec=3.0)

    def _fijar_tilt(self):
        """Mueve la cámara a tilt_angulo y espera la respuesta."""
        if self._cli_tilt is None:
            return
        if not self._cli_tilt.wait_for_service(timeout_sec=3.0):
            print('[aviso] move_tilt no responde.')
            return
        req = self._srv_tilt.Request()
        req.angle = float(self.cfg['tilt_angulo'])
        req.speed = float(self.cfg['tilt_velocidad'])
        fut = self._cli_tilt.call_async(req)
        rclpy.spin_until_future_complete(self.nodo, fut, timeout_sec=10.0)

    def _vaciar_cola(self):
        """Descarta los mensajes de blobs pendientes (anteriores o
        simultáneos a la acción)."""
        for _ in range(100):
            antes = self._n_blobs
            rclpy.spin_once(self.nodo, timeout_sec=0.0)
            if self._n_blobs == antes:
                return

    def _esperar_lectura_nueva(self, inicial=False):
        """Bloquea hasta recibir un mensaje de blobs POSTERIOR a este
        instante. Garantiza que la observación de step() corresponde a
        un instante posterior a la acción (requisito del apartado 5.2).
        Como color_blobs se publica a 5 Hz y también vacío, siempre llega
        un mensaje nuevo cada ~0,2 s, se vea o no la pelota."""
        objetivo = self._n_blobs + 1
        t0 = time.time()
        while self._n_blobs < objetivo:
            rclpy.spin_once(self.nodo, timeout_sec=0.05)
            if time.time() - t0 > self.cfg['espera_max_s']:
                raise RuntimeError(
                    'No llegan mensajes de color_blobs. Comprobar que '
                    "robobo_container está en marcha con el módulo 'blob'."
                    if inicial else
                    'Se ha interrumpido el flujo de color_blobs.')

    def _publicar_velocidad(self, v, w):
        msg = Twist()
        msg.linear.x = float(v)
        msg.angular.z = float(w)
        self.pub_vel.publish(msg)

    def _detener(self):
        for _ in range(3):
            self._publicar_velocidad(0.0, 0.0)
            time.sleep(0.05)


    def _preparar_reset(self):
        """Cliente del servicio de reinicio del módulo sim, por ROS 2.

        Se busca primero el nombre esperado (<ns_sim>/reset_simulation) y,
        si no aparece, cualquier servicio del grafo que termine en
        'reset_simulation' (por si el espacio de nombres es otro). Sólo si
        no hay ninguno se recurre a la biblioteca robobosim, como en el
        ejemplo."""
        nombre = self.cfg['ns_sim'] + '/reset_simulation'
        tipo = _esperar_tipo(self.nodo, nombre, servicio=True, espera_s=5.0)

        if tipo is None:
            candidatos = [(n, t[0]) for n, t in
                          self.nodo.get_service_names_and_types()
                          if n.endswith('reset_simulation') and t]
            if candidatos:
                nombre, tipo = candidatos[0]
                print('[aviso] Se usa {} (no {}).'.format(
                    nombre, self.cfg['ns_sim'] + '/reset_simulation'))

        if tipo is not None:
            self._srv_reset = get_service(tipo)
            self._cli_reset = self.nodo.create_client(self._srv_reset, nombre)
            return

        try:
            from robobosim.RoboboSim import RoboboSim
        except ImportError:
            sim = sorted(n for n, _ in self.nodo.get_service_names_and_types()
                         if '/sim' in n)
            raise RuntimeError(
                'No hay servicio reset_simulation en ROS 2 ni biblioteca '
                "robobosim.\n¿Está el puente lanzado con modules:=\"['blob','sim']\"?"
                '\nServicios con /sim en el grafo: {}'.format(sim or 'ninguno'))
        print('[aviso] No aparece {}; se usa robobosim.'.format(nombre))
        self._sim_lib = RoboboSim('host.docker.internal')
        self._sim_lib.connect()

    def _suscribir_pose(self, topico, atributo):
        tipo = _esperar_tipo(self.nodo, topico, espera_s=3.0)
        if tipo is None:
            print('[aviso] No aparece {}.'.format(topico))
            return

        def cb(msg):
            # mm y grados; suelo en el plano (x, z)
            setattr(self, atributo,
                    (msg.position.x, msg.position.z, msg.rotation.y))
        self.nodo.create_subscription(get_message(tipo), topico, cb, 1)

    def _reiniciar_escena(self):
        if self._cli_reset is not None:
            self._cli_reset.wait_for_service(timeout_sec=3.0)
            fut = self._cli_reset.call_async(self._srv_reset.Request())
            rclpy.spin_until_future_complete(self.nodo, fut, timeout_sec=5.0)
        elif self._sim_lib is not None:
            self._sim_lib.resetSimulation()
        time.sleep(0.5)


    def _medidas_blob(self):
        """(visible, x, size) normalizados a partir del último blob."""
        c = self.cfg
        if self._blob is None:
            return 0.0, self._ultima_x, 0.0
        bx, _, bs = self._blob
        x = (bx - c['blob_x_max'] / 2.0) / (c['blob_x_max'] / 2.0)
        x = float(np.clip(x, -1.0, 1.0))
        s = float(np.clip(bs / c['s_max'], 0.0, 1.0))
        self._ultima_x = x
        return 1.0, x, s

    def _observacion(self, visible, x, s):
        obs = [visible, x, s] + list(self.ultima_accion)
        return np.array(obs, dtype=np.float32)

    def _separacion(self):
        """Separación del anexo B.1, en metros: distancia entre el centro del
        seguidor y la pelota verde, cuya posición es la pose del guía
        desplazada pelota_offset_m hacia su parte trasera. None si no hay
        pose del seguidor o del guía.

        Rumbo: con rotación y = θ (grados), el robot mira hacia
        (sin θ, cos θ) en el plano (x, z). Comprobado con la escena: con
        θ = 0 el guía (z = -566) va por delante de la pelota (z = -684)."""
        if self._pose is None or self._sim_guia is None:
            return None
        try:
            g = self._sim_guia.getObjectLocation(self.cfg['guia_objeto'])
        except Exception:
            return None
        if not g:
            return None
        gx, gz = g['position']['x'], g['position']['z']
        th = np.radians(g['rotation']['y'])
        off = self.cfg['pelota_offset_m'] * 1000.0
        px = gx - off * np.sin(th)
        pz = gz - off * np.cos(th)
        fx, fz = self._pose[0], self._pose[1]
        return float(np.hypot(px - fx, pz - fz) / 1000.0)

    def _detectar_atasco(self, v):
        """True si en los últimos atasco_pasos pasos se ha ordenado avanzar
        (v >= atasco_v_min en todos) y el seguidor se ha desplazado menos de
        atasco_mm. Se compara con la pose de hace atasco_pasos pasos, no con
        la del paso anterior, para no confundir un atasco con que
        robot_location aún no se haya actualizado."""
        c = self.cfg
        if self._pose is None:          # sin módulo sim: no se detecta
            return False
        if v < c['atasco_v_min']:
            # Parado o marcha atrás a propósito: no cuenta como atasco
            self._poses_recientes.clear()
            return False
        self._poses_recientes.append((self._pose[0], self._pose[1]))
        if len(self._poses_recientes) < self._poses_recientes.maxlen:
            return False
        (x0, z0), (x1, z1) = self._poses_recientes[0], self._poses_recientes[-1]
        return bool(np.hypot(x1 - x0, z1 - z0) < c['atasco_mm'])



    def _recompensa(self, visible, x, s, choque, perdido, cambio_accion):
        """Los cuatro términos de espacios.txt más uno de suavidad.
        Coeficientes iniciales, a ajustar experimentalmente (y a declarar
        en la memoria).

          1. Distancia:   1 - |s - S_obj| / S_tol, recortado a [-1, 1]
                          (sólo visible). Vale 1 en el objetivo, 0 a una
                          tolerancia de distancia y -1 a dos o más: ir
                          demasiado lejos o demasiado cerca resta.
          2. Centrado:    1 - |x|, en [0, 1] (sólo visible)
          3. Visibilidad: -K_PERDIDO por cada paso sin ver al guía y
                          R_PERDIDO al terminar por pérdida prolongada
          4. Seguridad:   penalización creciente si s > S_cerca y
                          R_CHOQUE al terminar por colisión
          5. Suavidad:    -K_SUAVE * (|Δv| + |Δw|) de la acción normalizada
                          respecto al paso anterior, para que regule la
                          velocidad de forma progresiva y no a tirones.
        """
        c = self.cfg
        K_DIST = 1.0
        K_CENTRO = 0.3
        K_PERDIDO = 1.0
        K_CERCA = 2.0
        K_SUAVE = 0.1
        R_CHOQUE = -10.0
        R_PERDIDO = -10.0

        r = 0.0
        if visible:
            err = abs(s - c['s_objetivo']) / c['s_tolerancia']
            r_dist = 1.0 - min(err, 2.0)
            r_centro = 1.0 - abs(x)
            r += K_DIST * r_dist + K_CENTRO * r_centro

            if s > c['s_cerca']:
                exceso = (s - c['s_cerca']) / (c['s_choque'] - c['s_cerca'])
                r -= K_CERCA * min(exceso, 1.0)
        else:
            r -= K_PERDIDO

        r -= K_SUAVE * cambio_accion

        if choque:
            r += R_CHOQUE
        if perdido:
            r += R_PERDIDO
        return float(r)


    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._detener()

        if self.usar_simulador:
            # Ambos robots vuelven a la posición del escenario; el guía
            # arranca de nuevo con la configuración del simulador.
            self._reiniciar_escena()
            self._fijar_tilt()

        self.pasos = 0
        self.pasos_perdido = 0
        self.ultima_accion = np.zeros(2, dtype=np.float32)
        self._ultima_x = 0.0
        self._poses_recientes.clear()

        # Descartar lo acumulado durante el reinicio y esperar una lectura
        # tomada ya en la posición nueva.
        self._vaciar_cola()
        self._esperar_lectura_nueva()

        visible, x, s = self._medidas_blob()
        return self._observacion(visible, x, s), {}

    def step(self, accion):
        c = self.cfg
        accion = np.clip(np.asarray(accion, dtype=np.float32), -1.0, 1.0)
        # Cambio respecto a la acción anterior (término de suavidad)
        cambio_accion = float(np.sum(np.abs(accion - self.ultima_accion)))
        self.ultima_accion = accion

        # 1. Reescalar y publicar
        v = c['v_min'] + (accion[0] + 1.0) * 0.5 * (c['v_max'] - c['v_min'])
        w = float(accion[1]) * c['w_max']
        self._publicar_velocidad(v, w)

        # 2. Dejar actuar (paso_s < 0,5 s del temporizador de cmd_vel)
        time.sleep(c['paso_s'])

        # 3-4. Descartar lo antiguo y esperar un mensaje posterior
        self._vaciar_cola()
        self._esperar_lectura_nueva()

        # 5. Evaluar
        self.pasos += 1
        visible, x, s = self._medidas_blob()

        # Separación real (anexo B.1), con la pose del simulador. Sólo se
        # usa para decidir el fin del episodio y para registro (apartado 4).
        sep = self._separacion()

        if sep is not None:
            # Criterios del anexo B.3:
            #   colisión:     separación < sep_colision_m (0,12 m)
            #   guía perdido: separación > sep_perdido_m (0,90 m), o la
            #                 pelota sin detectarse durante pasos_perdido_max
            #                 pasos seguidos (3 s en el protocolo)
            self.pasos_perdido = 0 if visible else self.pasos_perdido + 1
            perdido = bool(sep > c['sep_perdido_m'] or
                           self.pasos_perdido >= c['pasos_perdido_max'])
            choque = bool(sep < c['sep_colision_m'])
        else:
            # Sin simulador: aproximación por el tamaño del blob.
            # Pelota visible pero más pequeña que s_lejos cuenta igual que
            # no verla para declarar el guía perdido.
            lejos = bool(visible and s < c['s_lejos'])
            self.pasos_perdido = (0 if (visible and not lejos)
                                  else self.pasos_perdido + 1)
            perdido = self.pasos_perdido >= c['pasos_perdido_max']
            choque = bool(visible and s >= c['s_choque'])

        # Atasco: choque con el entorno (señales, bordillos...). Se usa la
        # pose del simulador, que el apartado 4 permite para decidir el fin
        # del episodio (no entra en la observación ni en la recompensa).
        atascado = self._detectar_atasco(v)

        r = self._recompensa(visible, x, s, choque, perdido, cambio_accion)

        terminated = bool(choque or perdido or atascado)
        truncated = bool(self.pasos >= self.pasos_max)
        if terminated or truncated:
            self._detener()

        info = {
            'visible': bool(visible),
            'x': x,
            'tamano': s,
            # Separación real seguidor-pelota en m (None sin simulador)
            'separacion': sep,
            'choque': choque,
            'perdido': perdido,
            'atascado': atascado,
            # Pose real del seguidor (mm, grados), sólo para registro
            'pose_sim': self._pose,
        }

        if self.verbose:
            print('paso {:3d}  vis={:d} x={:+.2f} s={:.2f}  sep={}  v={:+.3f} '
                  'w={:+.3f}  r={:+.3f}{}'.format(
                      self.pasos, int(visible), x, s,
                      '{:.3f}'.format(sep) if sep is not None else '  -  ',
                      v, w, r,
                      '  CHOQUE' if choque else
                      '  ATASCO' if atascado else
                      ('  PERDIDO' if perdido else '')))

        return self._observacion(visible, x, s), r, terminated, truncated, info

    def close(self):
        try:
            self._detener()
        except Exception:
            pass
        for lib in (self._sim_lib, self._sim_guia):
            if lib is not None:
                try:
                    lib.disconnect()
                except Exception:
                    pass
        try:
            self.nodo.destroy_node()
        except Exception:
            pass


def calibrar():
    """Imprime en continuo el blob verde (bruto y normalizado).

    Sirve para fijar en p1_config.json:
      - blob_x_max: el valor de x con la pelota en el borde derecho
        (x centrada ≈ 0 con la pelota en el centro de la imagen).
      - s_max: tamaño bruto máximo observado antes de que la pelota
        empiece a cortarse por el borde inferior de la imagen.
      - s_objetivo: tamaño normalizado a la separación deseada.
      - s_cerca / s_choque: tamaños demasiado cerca / casi tocando.
      - s_lejos: tamaño normalizado con la pelota a 0,90 m.
    Ctrl-C para salir.
    """
    cfg = cargar_config()
    if not rclpy.ok():
        rclpy.init()
    nodo = Node('p1_calibracion')

    # Misma inclinación de cámara que usa el entorno tras cada reinicio;
    # si no, se calibra con otro tilt y los tamaños no corresponden.
    if cfg.get('tilt_angulo') is not None:
        nombre = cfg['ns_base'] + '/move_tilt'
        tipo_t = _esperar_tipo(nodo, nombre, servicio=True, espera_s=3.0)
        if tipo_t is None:
            print('[aviso] No aparece {}; no se fija el tilt.'.format(nombre))
        else:
            srv = get_service(tipo_t)
            cli = nodo.create_client(srv, nombre)
            if cli.wait_for_service(timeout_sec=3.0):
                req = srv.Request()
                req.angle = float(cfg['tilt_angulo'])
                req.speed = float(cfg['tilt_velocidad'])
                fut = cli.call_async(req)
                rclpy.spin_until_future_complete(nodo, fut, timeout_sec=10.0)
                print('Tilt fijado a {}'.format(cfg['tilt_angulo']))

    topico = cfg['ns_smartphone'] + '/color_blobs'
    tipo = _esperar_tipo(nodo, topico)
    if tipo is None:
        raise SystemExit('No aparece ' + topico)
    print('Tipo de {}: {}'.format(topico, tipo))

    estado = {'blob': None, 'n': 0}

    def cb(m):
        estado['blob'] = _blob_de_color(m, cfg['blob_color'],
                                       cfg['blob_size_min'])
        estado['n'] += 1
    nodo.create_subscription(get_message(tipo), topico, cb, 1)

    # La última columna cuenta los mensajes de color_blobs recibidos: si no
    # crece, la lectura está congelada (puente o simulador parados).
    print('{:>8s} {:>8s} {:>8s}   {:>6s} {:>6s}   {:>6s}'.format(
        'x', 'y', 'size', 'x_norm', 's_norm', 'msgs'))
    try:
        while rclpy.ok():
            rclpy.spin_once(nodo, timeout_sec=0.5)
            b = estado['blob']
            if b is None:
                print('{:>8s}   (no se ve la pelota)            {:6d}'.format(
                    '-', estado['n']))
            else:
                xn = (b[0] - cfg['blob_x_max'] / 2) / (cfg['blob_x_max'] / 2)
                sn = min(b[2] / cfg['s_max'], 1.0)
                print('{:8.1f} {:8.1f} {:8.1f}   {:+6.2f} {:6.2f}   {:6d}'.format(
                    b[0], b[1], b[2], xn, sn, estado['n']))
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()