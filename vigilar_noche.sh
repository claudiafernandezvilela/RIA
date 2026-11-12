#!/bin/bash
# Vigilancia nocturna de las evoluciones de C4 (configuración final).
# 1. dir_c4f_s6 hasta 25 generaciones (0-24): si se para, se reanuda.
# 2. Al terminar, dir_c4f_s8 (semilla 8, config_c4_final.json), 25 generaciones,
#    vigilada igual.
# Si la consola no cambia en COLGADO_S segundos, se da por colgada, se mata
# el proceso y se reanuda desde el último punto de control.
# RoboboSim tiene que seguir en Variable 10-40 con paradas.

RIA=/Users/claudiafernandezvilela/robotica/pc-robobo/macOS/docker-ros/ws/RIA
GEN=25
COLGADO_S=900          # 15 min sin escribir en la consola (un individuo tarda < 3 min)
MAX_REANUDAR=10        # por evolución, para no entrar en bucle si algo falla siempre
ESPERA_S=1800         # comprobación cada 30 min

reanudadas_s6=0
reanudadas_s8=0

log() { echo "[$(date '+%H:%M:%S')] $*"; }

corriendo() { docker exec pc-robobo pgrep -f "evolucionar.py" >/dev/null 2>&1; }

ultima_gen() {  # última generación del CSV, o -1
    local csv="$RIA/evoluciones/$1/evolucion.csv"
    [ -f "$csv" ] || { echo -1; return; }
    tail -1 "$csv" | cut -d, -f1 | grep -E '^[0-9]+$' || echo -1
}

lanzar() {  # $1 = argumentos de evolucionar.py, $2 = consola
    docker exec -d pc-robobo bash -c "source /opt/ros/jazzy/setup.bash && source /opt/ros/robobo/setup.bash && cd /docker-ros/ws/RIA && python3 -u evolucionar.py $1 >> $2 2>&1"
}

log "Vigilancia iniciada: dir_c4f_s6 hasta la generación $((GEN-1)), luego dir_c4f_s8."

while true; do
    if corriendo; then
        # ¿Colgada? Se mira la consola de la evolución que esté en marcha.
        if [ "$(ultima_gen dir_c4f_s6)" -lt $((GEN-1)) ]; then
            consola="$RIA/consola_dir_c4f_s6.log"
        else
            consola="$RIA/consola_dir_c4f_s8.log"
        fi
        if [ -f "$consola" ]; then
            edad=$(( $(date +%s) - $(stat -f %m "$consola") ))
            if [ "$edad" -gt "$COLGADO_S" ]; then
                log "$(basename "$consola") sin cambios desde hace $((edad/60)) min: se mata y se reanudará."
                docker exec pc-robobo pkill -f "evolucionar.py"
                sleep 20
                continue   # se reanuda ya, sin esperar otros 30 min
            fi
        fi
        log "En marcha: dir_c4f_s6 gen. $(ultima_gen dir_c4f_s6), dir_c4f_s8 gen. $(ultima_gen dir_c4f_s8)."
        sleep $ESPERA_S
        continue
    fi

    g6=$(ultima_gen dir_c4f_s6)
    if [ "$g6" -lt $((GEN-1)) ]; then
        if [ $reanudadas_s6 -ge $MAX_REANUDAR ]; then
            log "dir_c4f_s6 parada $MAX_REANUDAR veces: dejo de reanudar. Revisar el simulador."
            exit 1
        fi
        reanudadas_s6=$((reanudadas_s6+1))
        log "dir_c4f_s6 parada en la generación $g6: reanudo ($reanudadas_s6/$MAX_REANUDAR)."
        lanzar "--etiqueta dir_c4f_s6 --guia c4 --reanudar --generaciones $GEN --pasos-max 200" consola_dir_c4f_s6.log
        sleep $ESPERA_S
        continue
    fi

    g8=$(ultima_gen dir_c4f_s8)
    if [ "$g8" -ge $((GEN-1)) ]; then
        log "dir_c4f_s6 y dir_c4f_s8 terminadas. Fin de la vigilancia."
        exit 0
    fi
    if [ $reanudadas_s8 -ge $MAX_REANUDAR ]; then
        log "dir_c4f_s8 parada $MAX_REANUDAR veces: dejo de reanudar. Revisar el simulador."
        exit 1
    fi
    reanudadas_s8=$((reanudadas_s8+1))
    if ls "$RIA/evoluciones/dir_c4f_s8/chk/p2-"* >/dev/null 2>&1; then
        log "dir_c4f_s8 parada en la generación $g8: reanudo ($reanudadas_s8/$MAX_REANUDAR)."
        lanzar "--etiqueta dir_c4f_s8 --guia c4 --reanudar --generaciones $GEN --pasos-max 200" consola_dir_c4f_s8.log
    else
        # Sin ningún punto de control: se empieza de cero (una carpeta vacía
        # de un arranque fallido impediría crearla).
        [ -d "$RIA/evoluciones/dir_c4f_s8" ] && rm -r "$RIA/evoluciones/dir_c4f_s8"
        log "dir_c4f_s6 terminada. Lanzo dir_c4f_s8 (semilla 8) desde cero ($reanudadas_s8/$MAX_REANUDAR)."
        lanzar "--etiqueta dir_c4f_s8 --guia c4 --semilla 8 --generaciones $GEN --pasos-max 200 --poblacion 20 --episodios-individuo 2 --config-json config_c4_final.json" consola_dir_c4f_s8.log
    fi
    sleep $ESPERA_S
done
