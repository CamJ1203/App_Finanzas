"""
calculos.py — Lógica financiera de la app

Filosofía:
    INGRESOS (100%)
     Gastos previstos (fijos + estimaciones + provisiones/12)
    = REMANENTE
         pct_ahorro -> Ahorro protegido
         pct_ocio   -> Ocio disponible

    Gastos imprevistos → reducen  ahorro
    Gastos de ocio     → reducen el ocio disponible
    Sobrante al cierre → usuario elige: ahorro o ocio
"""

from database import (
    total_ingresos, total_sueldo, total_extras,
    total_gastos_importantes,
    obtener_gastos_generales, obtener_gastos_casa, obtener_gastos_importantes,
    obtener_estimaciones, obtener_gastos_fijos, obtener_provisiones,
    obtener_pct_ahorro, get_db,
)


# ─────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────

def _config_previstos(user_id: int) -> tuple:
    """
    Lee fijos, estimaciones y provisiones configurados.
    Devuelve (fijos, estimacs, provisiones, total_previstos).
    Centralizado para no repetir en cada función.
    """
    fijos      = obtener_gastos_fijos(user_id)
    estimacs   = obtener_estimaciones(user_id)
    provisiones= obtener_provisiones(user_id)
    total = round(
        sum(f["monto"]     for f in fijos) +
        sum(e["promedio"]  for e in estimacs) +
        sum(p["cuota_mes"] for p in provisiones),
        2
    )
    return fijos, estimacs, provisiones, total


# ─────────────────────────────────────────
# FUNCIÓN CENTRAL — estado del mes
# ─────────────────────────────────────────

def calcular_mes(user_id: int, mes: str) -> dict:
    """
    Calcula el estado financiero completo de un mes.
    Devuelve un dict con todos los valores para mostrar en la app.
    """
    # Ingresos
    ing_total  = total_ingresos(user_id, mes)
    ing_sueldo = total_sueldo(user_id, mes)
    ing_extras = total_extras(user_id, mes)

    # Gastos previstos
    fijos, estimacs, provisiones, total_previstos = _config_previstos(user_id)

    # Remanente
    #remanente = round(max(0, ing_total - total_previstos), 2)
    remanente = round(int(ing_total - total_previstos), 2)

    # Split ahorro / ocio sobre el remanente
    pct_ahorro, pct_ocio = obtener_pct_ahorro(user_id)
    ahorro_previsto = round(remanente * pct_ahorro, 2)
    ocio_previsto   = round(remanente * pct_ocio,   2)

    # Imprevistos y gastos casa — reducen ahorro y ocio proporcionalmente
    gastos_imp_lista  = obtener_gastos_importantes(user_id, mes)
    gastos_casa_lista  = obtener_gastos_casa(user_id, mes)
    total_casa_gastado = round(sum(g["monto"] for g in gastos_casa_lista), 2)
    total_imprevistos = round(sum(g["monto"] for g in gastos_imp_lista), 2)
    reduccion_ahorro  = round(total_imprevistos * pct_ahorro, 2)
    reduccion_ocio    = round(total_imprevistos * pct_ocio,   2)

    ahorro_real = round(((ing_total - total_casa_gastado) * pct_ahorro) - total_imprevistos, 2)
    ocio_base   = round(((ing_total - total_casa_gastado) * pct_ocio), 2)

    # Gastos de ocio reales
    gastos_ocio_lista  = obtener_gastos_generales(user_id, mes)
    total_ocio_gastado = round(sum(g["monto"] for g in gastos_ocio_lista), 2)
    ocio_disponible    = round(ocio_base - total_ocio_gastado, 2)

    # Sobrante de previstos = lo previsto menos lo realmente gastado en casa
    sobrante_previstos = round(total_previstos - total_casa_gastado, 2)

    return {
        # Ingresos
        "ing_total":          ing_total,
        "ing_sueldo":         ing_sueldo,
        "ing_extras":         ing_extras,
        # Previstos
        "total_previstos":    total_previstos,
        "detalle_fijos":      fijos,
        "detalle_estim":      estimacs,
        "detalle_provis":     provisiones,
        # Remanente y distribución
        "remanente":          remanente,
        "pct_ahorro":         pct_ahorro,
        "pct_ocio":           pct_ocio,
        "ahorro_previsto":    ahorro_previsto,
        "ocio_previsto":      ocio_previsto,
        # Imprevistos
        "total_imprevistos":  total_imprevistos,
        "gastos_imp_lista":   gastos_imp_lista,
        "reduccion_ahorro":   reduccion_ahorro,
        "reduccion_ocio":     reduccion_ocio,
        # Estado real
        "ahorro_real":        ahorro_real,
        "ocio_disponible":    ocio_disponible,
        "total_ocio_gastado": total_ocio_gastado,
        # Casa
        "total_casa_gastado": total_casa_gastado,
        "gastos_casa_lista":  gastos_casa_lista,
        # Sobrante al cierre
        "sobrante_previstos": sobrante_previstos,
        "mes":                mes,
    }


# ─────────────────────────────────────────
# ACUMULADOS HISTÓRICOS
# ─────────────────────────────────────────

def _meses_con_ingresos(user_id: int) -> list:
    """Lista de meses ('YYYY-MM') que tienen al menos un ingreso."""
    with get_db() as conn:
        filas = conn.execute("""
            SELECT DISTINCT substr(fecha,1,7) as mes
            FROM ingresos WHERE user_id = ?
            ORDER BY mes ASC
        """, (user_id,)).fetchall()
    return [f["mes"] for f in filas]


def _ahorro_total_acumulado(user_id: int) -> float:
    """
    Suma el ahorro_real de todos los meses con ingresos.
    Usa la misma fórmula que calcular_mes():
        ahorro_real = (ingresos - gastos_casa) * pct_ahorro - imprevistos
    """
    meses = _meses_con_ingresos(user_id)
    if not meses:
        return 0.0

    pct_a, _            = obtener_pct_ahorro(user_id)

    acumulado = 0.0
    for mes in meses:
        ing        = total_ingresos(user_id, mes)
        casa       = round(sum(g["monto"] for g in obtener_gastos_casa(user_id, mes)), 2)
        imp        = total_gastos_importantes(user_id, mes)
        ahorro_mes = round(((ing - casa) * pct_a) - imp, 2)
        acumulado += ahorro_mes
 
    return round(acumulado, 2)


def _ocio_total_acumulado(user_id: int) -> float:
    """
    Suma el ocio disponible de todos los meses con ingresos.
    Usa la misma fórmula que calcular_mes():
        ocio_base       = (ingresos - gastos_casa) * pct_ocio
        ocio_disponible = ocio_base - ocio_gastado
    """
    meses = _meses_con_ingresos(user_id)
    if not meses:
        return 0.0
 
    _, pct_o = obtener_pct_ahorro(user_id)
 
    acumulado = 0.0
    for mes in meses:
        ing      = total_ingresos(user_id, mes)
        casa     = round(sum(g["monto"] for g in obtener_gastos_casa(user_id, mes)), 2)
        ocio_base= round((ing - casa) * pct_o, 2)
        gastado  = round(sum(g["monto"] for g in obtener_gastos_generales(user_id, mes)), 2)
        acumulado += (ocio_base - gastado)
 
    return round(acumulado, 2)


# ─────────────────────────────────────────
# HISTÓRICO ANUAL
# ─────────────────────────────────────────

def historico_anual(user_id: int, anio: int) -> list:
    """
    Resumen mes a mes del año para la tabla comparativa.
    Solo incluye meses con algún dato.
    """
    _, _, _, total_prev = _config_previstos(user_id)
    pct_a, _            = obtener_pct_ahorro(user_id)

    MESES = ["Ene","Feb","Mar","Abr","May","Jun",
             "Jul","Ago","Sep","Oct","Nov","Dic"]
    resultado = []
    for i, nombre in enumerate(MESES, start=1):
        mes_str = f"{anio}-{i:02d}"
        ing     = total_ingresos(user_id, mes_str)

        # Solo incluir meses con datos
        if ing == 0:
            continue
        gastos_casa_lista  = obtener_gastos_casa(user_id, mes_str)
        total_casa_gastado = round(sum(g["monto"] for g in gastos_casa_lista), 2)
        imp    = total_gastos_importantes(user_id, mes_str)
        ahorro = round(((ing - total_casa_gastado) * pct_a) - imp, 2)
        ocio_g = round(sum(g["monto"] for g in obtener_gastos_generales(user_id, mes_str)), 2)

        resultado.append({
            "mes":         nombre,
            "ingresos":    ing,
            "previstos":   total_prev,
            "imprevistos": imp,
            "ocio_gast":   ocio_g,
            "ahorro":      ahorro,
        })
    return resultado