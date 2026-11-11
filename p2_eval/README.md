# Evaluación de los controladores de la P2

Protocolo del anexo B: episodios de 120 s con la red determinista y los
criterios de fallo del anexo B.3. 3 episodios por configuración.

## Semilla 2: id 1038

Genoma: `evoluciones/inc_s2c_w40/genomas/mejor_gen039.pkl`.
Registros: [`semilla2_id1038/`](semilla2_id1038/).

| Configuración | Completa | En banda 0,20-0,45 m | Separación media | Separación mínima | Pelota visible |
|---|---|---|---|---|---|
| C1 (Crucero 10-10) | 3/3 | 99 % | 0,33 m | 0,24 m | 100 % |
| C2 (Crucero 10-40) | 3/3 | 43-45 % | 0,44 m | 0,26 m | 100 % |
| C3 (Variable 10-40) | 3/3 | 60-73 % | 0,42-0,43 m | 0,28 m | 100 % |
| C4 (con paradas) | 0/2 | | | | |

El robot completa C1-C3 sin colisión ni pérdida del guía. En C2 pasa buena
parte del tiempo por encima de 0,45 m en las rectas, cuando el guía va a unos
0,20 m/s. Por eso su banda es la más baja. En C4 pierde al guía a los 21-27 s.

Tres episodios por configuración son pocos para afirmar que nunca fallará.

## Semilla 3

Pendiente: ningún genoma evaluado completa todavía C1-C3. Las evaluaciones
hechas están en `_descartadas/`:

| Genoma | Generación | C1 | C2 | C3 |
|---|---|---|---|---|
| 236 | mejor de la etapa C1 | 3/3 | sin evaluar | sin evaluar |
| 754 | 29, mejor antes de C3 | sin evaluar | 3/3 | sin evaluar |
| 803 | 32-33 | 0/3 | 3/3 | 1/3 |
| 918 | 35-36 | 0/3 | 1/3 | 0/3 |
| 971 | 37-39, mejor final | 0/3 | 0/3 | 1/3 |

Todos los genomas de la etapa C3 fallan en C1 de la misma forma: se acercan
al guía lento, la pelota sale de la imagen por abajo y, sin ver, siguen
avanzando hasta chocar o perderla.

## C4

Controlador evolucionado desde cero en C4 (`evoluciones/dir_c4_s5`): id 557,
3/3 episodios completados, 50,5 % en banda y separación media 0,45 m.
Detalle y resto de candidatos en [`c4/`](c4/README.md).

## Pruebas descartadas

En [`_descartadas/`](_descartadas/README.md).

Para evaluar un genoma, con el guía puesto a mano en la configuración indicada:

```bash
python3 evaluar.py --genoma evoluciones/inc_s2c_w40/genomas/mejor_gen039.pkl --config c2 --episodios 3 --carpeta p2_eval/semilla2_id1038
```
