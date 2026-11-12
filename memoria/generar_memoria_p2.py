#!/usr/bin/env python3
"""Genera memoria/RIA_P2_Memoria.docx con el formato de la memoria de la P1
(se usa como plantilla: estilos, márgenes y tablas).

    python3 memoria/generar_memoria_p2.py

Lo marcado como PENDIENTE sale en rojo: falta medirlo o escribirlo.
"""
import copy
import os
import re

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

DIR = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(DIR, 'RIA_P1_Memoria.docx')
SALIDA = os.path.join(DIR, 'RIA_P2_Memoria.docx')
FIGURAS = os.path.join(DIR, '..', 'figuras')

ROJO = RGBColor(0xC0, 0x00, 0x00)
ANCHO_TABLA = 9072  # dxa, como en la P1

doc = docx.Document(PLANTILLA)
cuerpo = doc.element.body
for el in list(cuerpo):
    if el.tag != qn('w:sectPr'):
        cuerpo.remove(el)

# Calibri 11 explícito (enunciado, apartado 9.1), también en los títulos
for nombre in ('Normal', 'Heading 1', 'Heading 2', 'Caption'):
    estilo = doc.styles[nombre]
    estilo.font.name = 'Calibri'
    rfonts = estilo.element.get_or_add_rPr().get_or_add_rFonts()
    for atr in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rfonts.set(qn(atr), 'Calibri')
doc.styles['Normal'].font.size = Pt(11)

n_tabla = [0]
n_figura = [0]


def _runs(p, texto, tam=None):
    """Texto con **negrita**, `código` y [PENDIENTE ...] en rojo."""
    for trozo in re.split(r'(\*\*[^*]+\*\*|`[^`]+`|\[PENDIENTE[^\]]*\])', texto):
        if not trozo:
            continue
        if trozo.startswith('**'):
            r = p.add_run(trozo[2:-2])
            r.bold = True
        elif trozo.startswith('`'):
            r = p.add_run(trozo[1:-1])
            r.font.name = 'Consolas'
        elif trozo.startswith('[PENDIENTE'):
            r = p.add_run(trozo)
            r.bold = True
            r.font.color.rgb = ROJO
        else:
            r = p.add_run(trozo)
        if tam:
            r.font.size = Pt(tam)
    return p


def centrado(texto, tam=None, negrita=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    r.bold = negrita
    if tam:
        r.font.size = Pt(tam)


def h1(texto):
    doc.add_paragraph(texto, style='Heading 1')


def h2(texto):
    doc.add_paragraph(texto, style='Heading 2')


def par(texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return _runs(p, texto)


def lista(items):
    for it in items:
        p = doc.add_paragraph(style='List Bullet') if 'List Bullet' in \
            [s.name for s in doc.styles] else doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if p.style.name != 'List Bullet':
            # La plantilla de la P1 no tiene estilo de lista: viñeta con
            # sangría francesa
            it = '•\t' + it
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.first_line_indent = Cm(-0.4)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.6))
        _runs(p, it)


def formula(texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    r.font.name = 'Cambria Math'
    r.italic = True


def pie(tipo, texto):
    p = doc.add_paragraph(style='Caption')
    if tipo == 'Tabla':
        n_tabla[0] += 1
        n = n_tabla[0]
    else:
        n_figura[0] += 1
        n = n_figura[0]
    _runs(p, '{} {}. {}'.format(tipo, n, texto))
    return n


def tabla(filas, anchos, pie_texto):
    """filas[0] es la cabecera. anchos en proporción; se escalan a 9072 dxa."""
    total = sum(anchos)
    dxa = [int(ANCHO_TABLA * a / total) for a in anchos]
    dxa[-1] = ANCHO_TABLA - sum(dxa[:-1])
    t = doc.add_table(rows=len(filas), cols=len(anchos))
    tblPr = t._tbl.tblPr
    for tag in ('w:tblW', 'w:tblBorders', 'w:tblLayout', 'w:tblCellMar'):
        for el in tblPr.findall(qn(tag)):
            tblPr.remove(el)
    # Orden del esquema: tblStyle, tblW, ..., tblBorders, tblLayout,
    # tblCellMar, tblLook
    bordes = '<w:tblBorders>' + ''.join(
        '<w:{} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'.format(b)
        for b in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')) + \
        '</w:tblBorders>'
    look = tblPr.find(qn('w:tblLook'))
    for s in ('<w:tblW w:w="{}" w:type="dxa"/>'.format(ANCHO_TABLA), bordes,
              '<w:tblLayout w:type="fixed"/>',
              '<w:tblCellMar><w:top w:w="40" w:type="dxa"/>'
              '<w:left w:w="80" w:type="dxa"/><w:bottom w:w="40" '
              'w:type="dxa"/><w:right w:w="80" w:type="dxa"/>'
              '</w:tblCellMar>'):
        if look is not None:
            look.addprevious(_xml(s))
        else:
            tblPr.append(_xml(s))
    grid = t._tbl.tblGrid
    for gc, w in zip(grid.findall(qn('w:gridCol')), dxa):
        gc.set(qn('w:w'), str(w))
    for i, fila in enumerate(filas):
        for j, texto in enumerate(fila):
            celda = t.rows[i].cells[j]
            tcPr = celda._tc.get_or_add_tcPr()
            for el in tcPr.findall(qn('w:tcW')):
                tcPr.remove(el)
            tcPr.insert(0, _xml('<w:tcW w:w="{}" w:type="dxa"/>'.format(dxa[j])))
            if i == 0:
                tcPr.append(_xml('<w:shd w:val="clear" w:color="auto" '
                                 'w:fill="D9D9D9"/>'))
            tcPr.append(_xml('<w:vAlign w:val="center"/>'))
            p = celda.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _runs(p, ('**' + texto + '**') if i == 0 and texto else texto, 8)
    pie('Tabla', pie_texto)


def figura(nombre, ancho_cm, pie_texto):
    ruta = os.path.join(FIGURAS, nombre)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.exists(ruta):
        p.add_run().add_picture(ruta, width=Cm(ancho_cm))
    else:
        _runs(p, '[PENDIENTE: figura {}]'.format(nombre))
    pie('Figura', pie_texto)


def _xml(s):
    """Elemento OOXML a partir de su texto (se declara el espacio w)."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    return parse_xml(re.sub(r'^<(w:\w+)', r'<\1 ' + nsdecls('w'), s))


# ---------------------------------------------------------------- portada
centrado('Práctica 2 — Seguimiento de un vehículo en la ciudad de Robobo '
         'con neuroevolución', 16, True)
centrado('Robótica Inteligente Aplicada · Grado en Inteligencia Artificial · '
         'Universidade da Coruña · Curso 2026/27')
centrado('Claudia Fernández Vilela y Sofía García Pérez')

# ------------------------------------------------------------- 1. Diseño
h1('1. Diseño')
par('Se parte del entorno de Gymnasium de la Práctica 1 (ROS 2, calibración '
    'y evaluador del anexo B). La red de NEAT sustituye a la política de '
    'SB3: recibe la observación y devuelve la acción en cada paso. Periodo '
    'de control ≈ 0,4 s por paso (0,2 s de espera más la siguiente lectura '
    'del blob). Multiplicador del simulador: '
    '[PENDIENTE: ×1, el mismo en evolución, evaluación y P1].')

h2('1.1 Espacios de observación y de acción')
par('La observación sólo usa sensores del seguidor recibidos por ROS 2: el '
    'blob verde y sus propias órdenes. Nada del módulo sim.')
tabla([
    ['Entrada', 'Definición', 'Rango', 'Si no se ve la pelota'],
    ['visible', '1 si se detecta el blob verde', '{0, 1}', '0'],
    ['x', '(x_blob − 50) / 50', '[−1, 1]', 'Última x (lado de la pérdida)'],
    ['s', 'tamaño del blob / 450', '[0, 1]',
     '**Último tamaño visto** (en la P1, 0)'],
    ['a₀, a₁ anteriores', 'Acción del paso anterior', '[−1, 1]',
     'Sin cambio'],
    ['Δs', '(s − s anterior) / 0,10', '[−1, 1]', '0'],
], [1.4, 2.6, 1.0, 2.6], 'Espacio de observación (6 entradas).')
par('Cambios respecto a la P1, todos preprocesado o escalado dentro del '
    'entorno (permitidos por el apartado 8):')
lista([
    '**Memoria del tamaño** (`obs_memoria`). Con s = 0 al perder la pelota, '
    'la red lo leía como «muy lejos» y aceleraba justo cuando debía frenar: '
    'fallo observado en la evaluación de los controladores 557 (C3) y 474 '
    '(C4). La x ya conservaba su último valor.',
    '**v_min = −0,05 m/s con recorte a v ≥ 0** (`v_sin_marcha_atras`). La '
    'acción se escala como v = v_min + (a₀ + 1)/2 · (v_max − v_min) y luego '
    'v = max(0, v). Con v_min = 0, la salida tanh nunca alcanza −1, así que '
    'v = 0 era inalcanzable: no existía una distancia de equilibrio y en las '
    'paradas del guía el seguidor acababa encima de él. Ahora toda salida '
    'a₀ < −0,71 da v = 0: se detiene sin saturar la neurona y **nunca va '
    'marcha atrás**, como se recomendó en la P1.',
    '**w_max = 0,4 rad/s** (0,8 en la P1): con 0,8 la red giraba de más y '
    'perdía la pelota de lado.',
])
tabla([
    ['Acción', 'Rango físico', 'Justificación'],
    ['v (a₀)', '[0; 0,30] m/s (v_min −0,05 recortada a 0)',
     'Detenerse sin saturar la tanh; sin marcha atrás'],
    ['w (a₁)', '[−0,4; 0,4] rad/s', 'Evitar giros excesivos'],
], [1.0, 3.0, 4.0], 'Espacio de acción (continuo, Box([−1, 1]²)).')

h2('1.2 Red')
par('6 entradas, 2 salidas, sin nodos ocultos al inicio y conexión inicial '
    'completa directa (`full_direct`), sólo hacia delante. Activación tanh en '
    'todos los nodos (tanh(2,5·z) en NEAT-Python), de modo que las salidas '
    'están en [−1, 1], el rango del espacio de acción. Agregación por suma; '
    'activación y agregación no mutan.')

h2('1.3 Función de calidad')
par('Se calcula al final de cada episodio a partir del registro de pasos. '
    'Usa información privilegiada del simulador: la separación real a la '
    'pelota (pose del guía desplazada 0,08 m) y el desplazamiento del guía '
    'para detectar sus paradas. Por cada paso vivo t (sin choque, pérdida ni '
    'atasco):')
formula('r_t = (0,2 + 0,6·q_sep + 0,2·q_x) · f_parada')
formula('Q = 100 · Σ r_t / N − 10 · [choque, atasco o guía sin arrancar]'
        ',   Q ∈ [−10, 100]')
tabla([
    ['Término', 'Fórmula', 'Coef.', 'Magnitud', 'Por qué'],
    ['Vivo', '1', '0,2', '—',
     'Distingue malos de menos malos desde la generación 0'],
    ['Separación', 'q_sep = 1 en [0,30; 0,45] m; lineal hasta 0 en 0,12 m y '
     'en 0,70 m', '0,6', 'Separación real (privilegiada)',
     'Término principal: la tarea'],
    ['Centrado', 'q_x = min(1, (1 − |x|)/0,8) si se ve; 0 si no', '0,2',
     'x del blob', 'Mantener la pelota en la imagen'],
    ['Parada', 'f = max(0, 1 − v/0,05) con el guía parado; 1 si no', '—',
     'v ordenada; desplazamiento del guía (privilegiado)',
     'Sin él la evolución usaba las paradas para acercarse'],
    ['Choque', 'se resta al final', '10', 'Desenlace',
     'Penaliza colisión, atasco o quedarse quieto'],
], [1.1, 2.6, 0.6, 1.7, 2.2], 'Términos de la calidad final.')
lista([
    'N = 200 es el número máximo de pasos, no los vividos: un episodio cortado '
    'pronto puntúa menos. Con 2 episodios por individuo, la calidad es la '
    'media.',
    'Guía parado: la pelota se desplaza menos de 4 mm por paso durante 2 pasos '
    '(≈ 0,01 m/s durante más de 0,5 s, el criterio del anexo B.1).',
    'La banda puntúa al máximo desde 0,30 m y no desde 0,20 m porque a unos '
    '0,23 m la pelota sale de la imagen por abajo y el seguidor queda ciego.',
    'Si a los 10 s el guía no ha arrancado (no arranca hasta que el seguidor '
    'se acerca), el episodio se corta y se resta 10: si no, quedarse quieto '
    'mirando la pelota daba Q ≈ 44.',
    'A bordo podrían calcularse el término de centrado y uno aproximado de '
    'separación a partir del tamaño del blob; la parada del guía y la '
    'separación real necesitan el simulador.',
])
par('**Formulaciones comparadas.** Se probaron cuatro, con los '
    'comportamientos de la Tabla 4:')
tabla([
    ['', 'Formulación', 'Evolución', 'Comportamiento obtenido'],
    ['F1', 'Banda 0,25-0,45 m, sin término de parada',
     'Semillas 2 y 3, incremental C1→C3, 40 gen.',
     'Resuelve C1-C3 (id 1038, 9/9), 0/2 en C4: se pega al guía parado, '
     'entra en la zona ciega y lo pierde'],
    ['F2', 'Banda 0,30-0,45 m', '`dir_c4_s5`, C4, 35 gen.',
     'id 557: 3/3 en C4, pero en 16 de 23 paradas frena sin llegar a '
     'detenerse'],
    ['F3', 'F2 + término de parada + 3 puntos menos por parada no superada',
     '`dir_c4p_s6`, `_s7`',
     'Con v_min = 0 pararse era imposible: la penalización castigaba a todos '
     'por igual y la evolución no avanzaba (s6) o avanzaba lento (s7)'],
    ['F4 (final)', 'F2 + término de parada sin penalización; v_min −0,05 '
     'recortada y memoria del tamaño', '`dir_c4f_s6`, `_s7`, `_s8`, `_s9`',
     'id 437: 12/12 en C1-C4; se detiene en las paradas'],
], [0.8, 2.6, 2.0, 3.6], 'Formulaciones de la calidad y comportamientos a los '
   'que dieron lugar.')

h2('1.4 Evaluación de cada individuo')
lista([
    'Guía en C4 (Variable 10-40 con paradas; `Stop times` 2-5 s, `Stop '
    'chances` 60) durante toda la evolución.',
    '2 episodios por individuo de 200 pasos como máximo (≈ 77 s).',
    'Cada episodio empieza con un reinicio de la escena: ambos robots en su '
    'posición inicial y el seguidor parado.',
    'Fin anticipado: colisión (< 0,12 m), guía perdido (> 0,90 m o 7 pasos '
    'sin ver la pelota), atasco o guía sin arrancar a los 10 s.',
])

h2('1.5 Parámetros de NEAT')
tabla([
    ['Parámetro', 'Valor', 'Parámetro', 'Valor'],
    ['Población', '20', 'Umbral de compatibilidad', '0,8'],
    ['Generaciones', '25', 'Coef. disjuntos / pesos', '1,0 / 0,5'],
    ['Estancamiento máximo', '8 gen.', 'Elitismo (por especie)', '1'],
    ['Supervivencia', '0,3', 'Tamaño mínimo de especie', '2'],
    ['Mutación de pesos', 'p 0,3; potencia 0,1; reemplazo 0,02',
     'Mutación de sesgos', 'p 0,3; potencia 0,1; reemplazo 0,02'],
    ['Pesos iniciales', 'N(0; 0,3), límites ±5', 'Sesgos iniciales',
     'N(0; 0,1), límites ±5'],
    ['Añadir / quitar conexión', '0,3 / 0,1', 'Añadir / quitar nodo',
     '0,1 / 0,05'],
    ['Activar / desactivar conexión', '0,01', 'Semillas', '6, 7, 8, 9'],
], [2.2, 2.3, 2.2, 2.3], 'Parámetros de NEAT (config-p2.ini).')
par('[PENDIENTE: indicar qué valores cambian respecto a las indicaciones '
    'técnicas y por qué; p. ej. el umbral de 0,8 para que con 20 individuos '
    'haya varias especies.]')

# ----------------------------------------------------------- 2. Evolución
h1('2. Evolución')
par('Controlador único evolucionado desde cero con el guía en C4 y la '
    'formulación F4, con cuatro semillas. La calidad teórica va de −10 a '
    '100.')
tabla([
    ['Evolución', 'Semilla', 'Generaciones', 'Evaluaciones', 'Pasos',
     'Horas', 'Mejor (última gen.)', 'Media (última gen.)'],
    ['`dir_c4f_s6`', '6', '25', '1000', '63 905', '7,35', '94,6', '58,6'],
    ['`dir_c4f_s7`', '7', '25', '1000', '59 736', '6,40', '90,4', '40,2'],
    ['`dir_c4f_s8`', '8', '25', '1000', '32 696', '3,90', '15,1', '8,9'],
    ['`dir_c4f_s9`', '9', '[PENDIENTE]', '', '', '', '', ''],
], [1.5, 0.8, 1.1, 1.1, 0.9, 0.8, 1.4, 1.4], 'Coste de cada evolución de la '
   'configuración final (población 20, 2 episodios por individuo, 200 '
   'pasos).')
figura('evolucion_c4f.png', 15, 'Calidad del mejor individuo y media de la '
       'población: media de las semillas y banda [PENDIENTE: mín-máx o '
       'desviación típica]. Población 20, 2 episodios por individuo, 200 '
       'pasos; [PENDIENTE: pasos y horas totales].')
figura('especies_c4f.png', 15, 'Número y tamaño de las especies '
       '(semilla 6).')
par('**Comentario.** La población inicial (redes aleatorias) obtiene un '
    'mejor de 4-6 y una media de 1-2: es la línea base. Las semillas 6 y 7 '
    'despegan a partir de la generación 10-12 y se estabilizan en 90-95 '
    'desde la 17, con medias de 40-58. La 8 no despega (mejor 15-47, media '
    '≈ 10): con 20 individuos el resultado depende mucho de la semilla. '
    '[PENDIENTE: semilla 9 y especies.]')
par('**Ruido de la calidad.** La mejor calidad de una generación puede bajar '
    'respecto a la anterior porque NEAT-Python reevalúa a todos los '
    'individuos. Por eso se eligieron candidatos que mantienen la calidad en '
    'varias generaciones (276 en la semilla 7: entre 89 y 91 en 7 '
    'generaciones) y se reevaluaron con el anexo B antes de elegir.')
par('**Simulador en segundo plano.** Con el ordenador desatendido (RoboboSim '
    'en segundo plano o pantalla apagada) el simulador se comporta distinto: '
    'los controladores 376, 437 y 310 completaron 0 de 9 episodios en C4 '
    'evaluados así y 8 de 9 con la ventana en primer plano. Esto explica '
    'saltos bruscos de calidad en la semilla 6 (generaciones 10-15). Desde '
    'entonces se evoluciona y evalúa con RoboboSim visible.')

# --------------------------------------------------------- 3. La red
h1('3. La red obtenida')
figura('red_437.png', 9, 'Topología del controlador final (id 437, '
       'semilla 6, generación 24). Verde: pesos positivos; rojo: '
       'negativos; grosor proporcional al peso.')
par('El 437 no tiene nodos ocultos: 2 nodos de salida y 7 conexiones '
    'activas, con a = tanh(2,5·z):')
formula('z_v = 0,23·visible − 0,08·x − 0,75·s + 0,04·a₀ + 0,09·a₁ − 0,07')
formula('z_w = 0,31·x + 0,10·s − 0,02')
lista([
    '**Velocidad**: es un control proporcional a la distancia. Acelera si ve '
    'la pelota (+0,23) y frena con su tamaño (−0,75·s). La salida baja de '
    '−0,71 (v = 0) cuando s ≳ 0,69, es decir, se detiene cuando está cerca '
    'del guía parado. [PENDIENTE: separación equivalente con la '
    'calibración.]',
    '**Giro**: proporcional a x, hacia el lado de la pelota.',
    '**Entradas que no usa**: Δs no tiene conexión; las acciones anteriores '
    'apenas influyen (0,04 y 0,09).',
    '**Frente al controlador del reto**: [PENDIENTE: comparar con las '
    'ganancias del controlador programado a mano]. La estructura es la '
    'misma idea (v según el tamaño, w según x), con las ganancias '
    'encontradas por la evolución.',
])

# -------------------------------------------------------- 4. Resultados
h1('4. Resultados')
h2('4.1 Protocolo del anexo B')
tabla([
    ['Config.', 'Completados', 'Desenlaces', '% en banda', 'Sep. media',
     'Desv. media', '% < 15°'],
    ['C1', '3/3 (100 %)', '—', '99,3', '0,351 m', '2,9°', '99,6'],
    ['C2', '3/3 (100 %)', '—', '49,0', '0,423 m', '4,2°', '94,3'],
    ['C3', '3/3 (100 %)', '—', '71,7', '0,419 m', '4,5°', '94,0'],
    ['C4', '3/3 (100 %)', '—', '70,7', '0,413 m', '4,2°', '94,0'],
    ['Total', '12/12 (100 %)', '—', '72,7', '0,401 m', '4,0°', '95,5'],
], [1.0, 1.4, 1.2, 1.1, 1.1, 1.1, 1.0], 'Métricas del anexo B del '
   'controlador final (id 437), 3 episodios de 120 s por configuración.')
par('**Paradas (C4)**: 18 paradas del guía; 11 superadas; en 2 el seguidor '
    'no llega a detenerse; las 5 restantes ocurren al final del episodio, sin '
    'los 10 s de margen para comprobarlas. El 557 (F2), en cambio, sólo '
    'superaba 6 de 23.')
par('En C2 el porcentaje en banda es el más bajo: en las rectas el guía va a '
    'unos 0,20 m/s y el seguidor se queda por encima de 0,45 m. La pelota se '
    've el 99-100 % del tiempo y la separación mínima es de 0,25 m: no entra '
    'en la zona ciega.')
par('**Segundo candidato**: id 276 (semilla 7), C1 3/3 y C2 3/3; '
    '[PENDIENTE: C3 y C4].')

h2('4.2 Línea base')
par('[PENDIENTE: métricas del anexo B de la población inicial o de la '
    'política aleatoria, y del controlador del reto.]')

h2('4.3 Comparación con la Práctica 1')
tabla([
    ['', 'P1 (SAC)', 'P2 (NEAT, id 437)'],
    ['C1 / C2 / C3 completados', '[PENDIENTE]', '3/3 · 3/3 · 3/3'],
    ['% en banda C1 / C2 / C3', '[PENDIENTE]', '99,3 · 49,0 · 71,7'],
    ['Pasos del entorno', '[PENDIENTE]', '63 905 (sólo la evolución final)'],
    ['Horas de reloj', '[PENDIENTE]', '7,35'],
    ['Tamaño', '[PENDIENTE: parámetros de la red SAC]',
     '2 nodos, 7 conexiones (9 parámetros con los sesgos)'],
    ['C4', 'No se evaluó en la P1', '3/3'],
], [2.4, 3.0, 3.6], 'Comparación con la política final de la P1, '
   'evaluadas en la misma sesión.')

# ------------------------------------------------- 5. Entorno real
h1('5. Transferencia al entorno real')
par('[PENDIENTE]')

# --------------------------------------------------- 6. Conclusiones
h1('6. Conclusiones')
lista([
    'NEAT encuentra una red mínima (sin ocultas, 7 conexiones) e '
    'interpretable que resuelve C1-C4 con un único controlador, frente a la '
    'red de la P1, que es una caja negra.',
    'El coste es el tiempo real de simulación: 6-7 h por semilla. La calidad '
    'es ruidosa y depende mucho de la semilla (una de cuatro no aprendió).',
    'Problemas encontrados y cómo se abordaron: la imposibilidad de '
    'detenerse con v ≥ 0 y salida tanh (v_min negativa con recorte); la '
    'evolución acercándose al guía parado en vez de detenerse (término de '
    'parada); la aceleración al perder la pelota (memoria del tamaño); la '
    'zona ciega por debajo de 0,23 m (banda desde 0,30 m); el simulador '
    'en segundo plano.',
    'Mejoras: más episodios por individuo para reducir el ruido, población '
    'mayor y evolucionar con las cuatro configuraciones del guía alternadas.',
])

doc.save(SALIDA)
print('Guardado en', SALIDA)
