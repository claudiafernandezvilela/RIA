# Evaluación en C4

Guía en Variable 10-40 con paradas (`Stop times` 2-5 s, `Stop chances` 60, las
mismas que en la evolución). Episodios de 120 s. El anexo B pide 2 episodios
en C4; aquí se hicieron 3 o más.

Controlador de C4: **id 437** (`evoluciones/dir_c4f_s6/genomas/mejor_gen024.pkl`),
configuración final, 3/3 episodios completados. Es también el controlador
final de C1-C3 (`../semilla6_c4f_id437/`, 9/9).

Todas las evaluaciones de la configuración final se hicieron con RoboboSim en
primer plano. Hechas con el ordenador desatendido, el 376, el 437 y el 310
completaron 0/9 (se descartaron); `prueba_id193/` se hizo antes de detectarlo.

Antes, el controlador de C4 era el **id 557**
(`evoluciones/dir_c4_s5/genomas/mejor_gen033.pkl`), 3/3 episodios completados.

El 557 evaluado también en C1-C3 (registros en `c4_dir_id557/`): C1 3/3,
C2 3/3, C3 1/3. En C3 oscila de lado a lado (x de la pelota entre −0,4 y
+0,4) a unos 0,45 m; en una curva con el guía acelerando la pelota sale de la
imagen por un lado y, sin verla, avanza a 0,17-0,22 m/s girando hacia el
último lado visto: una vez se aleja (perdido a 20 s) y otra alcanza al guía
(colisión a 43 s). En C4 el guía se para a menudo y pasa menos tiempo rápido
en las curvas, por eso ahí no le ocurrió en 3 episodios.

| Carpeta | Genoma | Evolución | Completa | En banda | Separación media | Cómo falla |
|---|---|---|---|---|---|---|
| `c4f_s6_id437/` | 437, gen. 24 (mejor final) | `dir_c4f_s6` | **3/3** | 70,7 % | 0,41 m | No falla. Separación mínima 0,25 m. De 18 paradas supera 11, en 2 no queda quieto y 5 sin margen de 10 s |
| `c4f_s6_id310/` | 310, gen. 17-18 | `dir_c4f_s6` | **3/3** | 61,8 % | 0,43 m | No falla. De 19 paradas supera 13; en 6 no queda quieto |
| `c4f_s6_id376/` | 376, gen. 21-22 | `dir_c4f_s6` | 2/3 | 65,8 % | 0,42 m | Pierde al guía a los 97 s. De 17 paradas supera 11; en 4 no queda quieto |
| `prueba_id193/` | 193, gen. 10-12 | `dir_c4f_s6` | 0/2 | | | Pierde al guía a los 7 s y a los 69 s. Evaluado sin comprobar que RoboboSim estaba en primer plano: no concluyente |
| `c4_dir_id571/` | 571, gen. 34 (mejor final) | `dir_c4_s5` | **3/3** | 74,8 % | 0,40 m | No falla en C4 (separación mínima 0,22 m). De 21 paradas supera 4. En C1-C3: C1 2/3, C2 0/3, C3 3/3. En C2 pierde la pelota de lado con el guía rápido y, sin verla, acelera a 0,19-0,22 m/s |
| `c4_dir_id557/` | 557, gen. 33-34 (4/4 episodios en la evolución) | `dir_c4_s5` | **3/3** | 50,5 % | 0,45 m | No falla. Separación mínima 0,26 m y pelota visible el 100 % del tiempo: no entra en la zona ciega. De 23 paradas del guía supera 6; en 16 frena a 0,01-0,03 m/s pero no llega a quedar quieto (< 0,01 m/s durante 0,5 s) |
| `c4_id1567/` | 1567, gen. 59 | `inc_s2c_w40_c4` | 2/9 | 81,0 % | 0,38 m | Se pega al guía parado, la pelota sale de la imagen por abajo, acelera y choca. Al arrancar en curva, la pierde y gira al lado contrario |
| `c4_id1523/` | 1523, gen. 57 | `inc_s2c_w40_c4` | 1/3 | 66,6 % | 0,42 m | Pierde la pelota cuando el guía arranca en curva. En el episodio 2 el guía saltó a su posición inicial a los 84,8 s (fallo del simulador) |
| `c4_id1241/` | 1241, gen. 46-47 | `inc_s2c_w40_c4` | 1/3 | 65,7 % | 0,41 m | |
| `c4_id1306/` | 1306, gen. 49 | `inc_s2c_w40_c4` | 0/3 | 65,9 % | 0,40 m | |
| `c4_dir_id474/` | 474, gen. 28-32 (10/10 episodios en la evolución) | `dir_c4_s5` | 1/3 | 56,4 % | 0,43 m | Espera bien al guía parado, pero al acercarse a 0,20 m la pelota sale de la imagen por abajo y, sin verla, avanza a 0,11-0,21 m/s y adelanta al guía (26 s y 74 s) |
| `c4_dir_id295/` | 295, gen. 16-17 | `dir_c4_s5` | 1/3 | 16,5 % | 0,58 m | Demasiado lento: con el guía lejos no pasa de 0,08-0,15 m/s y lo pierde a 0,9 m |

El 1038 (semilla 2, sin evolucionar en C4) completa 0/2: registros en
`../semilla2_id1038/`.

Causa común en la evolución incremental (1567): al dejar de ver la pelota,
`visible` y `tamaño` pasan a 0. El sesgo de `w` (−0,71) deja de estar
compensado por `visible` (+0,66) y la red gira a la izquierda casi al máximo.
Sin `tamaño`, desaparece el freno (`tamaño→v` −1,25) y acelera.

`c4_id1523/p2_inc_s2c_w40_c4_id1523_c4_ep4.csv` está vacío: es un episodio
interrumpido y no cuenta.
