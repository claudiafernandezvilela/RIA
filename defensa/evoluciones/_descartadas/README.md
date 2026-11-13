# Evoluciones descartadas y pruebas

Se conservan como evidencia de lo probado. Ninguna da el controlador final.

Los datos salen de `evolucion.csv` y `entorno.json` de cada carpeta. `Mejor` es
la calidad máxima de cada tramo.

| Carpeta | Semilla | `v_max` | `w_max` | Tramos (guía/pasos, generaciones, mejor) | Nota |
|---|---|---|---|---|---|
| `c1_s1` | 1 | 0,20 | 0,8 | C1/175, 0-39, 75,5 | |
| `c1_s1_saturada` | 1 | 0,20 | 0,8 | C1/175, 0-13, 28,2; C1/125, 14, 14,6 | |
| `c1_s2` | 2 | 0,20 | 0,8 | C1/245, 0-29, 99,3 | Evolución directa en C1 |
| `c2_s1` | 1 | 0,20 | 0,8 | C2/125, 0-29, 55,1 | |
| `c2_s1_umbral13` | 1 | 0,20 | 0,8 | C2/125, 0-29, 29,2 | |
| `inc_s2` | 2 | 0,20 | 0,8 | C1/245, 0-9, 99,1; C2/175, 10-19, 93,7 | |
| `inc_s2c` | 2 | 0,20 | 0,8 | C1/245, 0-9, 98,8; C1/300, 10-14, 99,0; C2/300, 15-32, 38,8 | Sus generaciones 0-9 son el origen de la evolución final |
| `inc_s2c_c1_extra` | 2 | | | C1/245, 0-9, 98,8; C2/300, 10-24, 99,4 | Generaciones extra con el guía en C1 |
| `inc_s2c_r10` | 2 | 0,20 | 0,8 | C1/245, 0-9, 98,8; C2/175, 10-19, 22,2 | |
| `inc_s2c_v30` | 2 | 0,30 | 0,8 | C1/245, 0-9, 98,8; C2/175, 10-19, 77,3; C2/300, 20-29, 69,5 | Contiene el id 404 (`genomas/mejor_gen015.pkl`) |
| `inc_s2c_v30w` | 2 | 0,30 | 0,4 | Nunca se lanzó | Copia preparada desde `p2-16`. Su `evolucion.csv` son filas de `inc_s2c_v30`, no resultados propios |
| `inc_s2c_w40_gen10_guia_c1` | 2 | | | C2/175, 10-12, 98,4 | Guía en C1 por error, aunque el CSV anota C2 |
| `inc_s2m` | 2 | 0,20 | 0,8 | C1/245, 0-9, 41,4 | Observación con memoria del último avistamiento |
| `inc_s2v` | 2 | 0,30 | 0,8 | C1/245, 0-9, 24,1 | |

Las configuraciones de estas pruebas están en `../../config_descartadas/`.
