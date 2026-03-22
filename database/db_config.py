from .db_core import get_db

# ─────────────────────────────────────────
# GASTOS FIJOS
# ─────────────────────────────────────────

def guardar_gasto_fijo(user_id, concepto, monto):
    """Crea o reactiva un gasto fijo. Si existía desactivado lo reactiva."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO config_gastos_fijos (user_id, concepto, monto, activo)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, concepto) DO UPDATE SET
                monto  = excluded.monto,
                activo = 1
        """, (user_id, concepto, monto))

def obtener_gastos_fijos(user_id):
    with get_db() as conn:
        filas = conn.execute(
            "SELECT * FROM config_gastos_fijos WHERE user_id = ? AND activo = 1",
            (user_id,)
        ).fetchall()
    return [dict(f) for f in filas]

def desactivar_gasto_fijo(user_id, id):
    with get_db() as conn:
        conn.execute(
            "UPDATE config_gastos_fijos SET activo = 0 WHERE id = ? AND user_id = ?",
            (id, user_id)
        )


# ─────────────────────────────────────────
# ESTIMACIONES
# ─────────────────────────────────────────

def guardar_estimacion(user_id, concepto, promedio):
    """Crea o reactiva una estimación. Si existía desactivada la reactiva."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO config_estimaciones (user_id, concepto, promedio, activo)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, concepto) DO UPDATE SET
                promedio = excluded.promedio,
                activo   = 1
        """, (user_id, concepto, promedio))

def obtener_estimaciones(user_id):
    with get_db() as conn:
        filas = conn.execute(
            "SELECT * FROM config_estimaciones WHERE user_id = ? AND activo = 1",
            (user_id,)
        ).fetchall()
    return [dict(f) for f in filas]

def desactivar_estimacion(user_id, id):
    with get_db() as conn:
        conn.execute(
            "UPDATE config_estimaciones SET activo = 0 WHERE id = ? AND user_id = ?",
            (id, user_id)
        )


# ─────────────────────────────────────────
# PROVISIONES
# ─────────────────────────────────────────

def guardar_provision(user_id, concepto, monto_anual):
    """Crea o reactiva una provisión. Si existía desactivada la reactiva."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO config_provisiones (user_id, concepto, monto_anual, activo)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, concepto) DO UPDATE SET
                monto_anual = excluded.monto_anual,
                activo      = 1
        """, (user_id, concepto, monto_anual))

def obtener_provisiones(user_id):
    with get_db() as conn:
        filas = conn.execute(
            "SELECT * FROM config_provisiones WHERE user_id = ? AND activo = 1",
            (user_id,)
        ).fetchall()
    resultado = []
    for f in filas:
        p = dict(f)
        p["cuota_mes"] = round(p["monto_anual"] / 12, 2)
        resultado.append(p)
    return resultado

def desactivar_provision(user_id, id):
    with get_db() as conn:
        conn.execute(
            "UPDATE config_provisiones SET activo = 0 WHERE id = ? AND user_id = ?",
            (id, user_id)
        )