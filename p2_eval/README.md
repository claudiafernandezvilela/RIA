# Evaluación del controlador final de la P2

Protocolo del anexo B: 3 episodios de 120 s por configuración, con la red
determinista y los criterios de fallo del anexo B.3.

## Semilla 2: id 1038

Genoma: `evoluciones/inc_s2c_w40/genomas/mejor_gen039.pkl`.
Registros: [`semilla2_id1038/`](semilla2_id1038/).

| Configuración | Completa | En banda 0,20-0,45 m | Separación media | Separación mínima | Pelota visible |
|---|---|---|---|---|---|
| C1 (Crucero 10-10) | 3/3 | 99 % | 0,33 m | 0,24 m | 100 % |
| C2 (Crucero 10-40) | 3/3 | 43-45 % | 0,44 m | 0,26 m | 100 % |
| C3 (Variable 10-40) | 3/3 | 60-73 % | 0,42-0,43 m | 0,28 m | 100 % |

El robot completa las tres configuraciones sin colisión ni pérdida del guía. En
C2 pasa buena parte del tiempo por encima de 0,45 m en las rectas, cuando el
guía va a unos 0,20 m/s. Por eso su banda es la más baja.

Tres episodios por configuración son pocos para afirmar que nunca fallará.

## Segunda semilla

Pendiente, con el protocolo de [`../evoluciones/README.md`](../evoluciones/README.md).
Sus registros irán en `semillaN_idNNNN/`.

## Pruebas descartadas

En [`_descartadas/`](_descartadas/README.md).

Para evaluar un genoma, con el guía puesto a mano en la configuración indicada:

```bash
python3 evaluar.py --genoma evoluciones/inc_s2c_w40/genomas/mejor_gen039.pkl --config c2 --episodios 3 --carpeta p2_eval/semilla2_id1038
```
