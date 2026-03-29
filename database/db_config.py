import streamlit as st
from .db_core import get_db

# ─────────────────────────────────────────
# GASTOS FIJOS
# ─────────────────────────────────────────

def guardar_gasto_fijo(user_id, concepto, monto):
    """Crea o reactiva un gasto fijo. Si existía desactivado lo reactiva."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO config_gastos_fijos (user_id, concepto, monto, activo)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, concepto) DO UPDATE SET
                monto  = excluded.monto,
                activo = excluded.activo
        """, (user_id, concepto, monto, True))
    st.cache_data.clear()

@st.cache_data(ttl=600)  # Cachea los gastos fijos hasta que haya cambios en configuración
def obtener_gastos_fijos(user_id):
    with get_db() as conn:
        filas = conn.execute(
            "SELECT * FROM config_gastos_fijos WHERE user_id = ? AND activo = ?",
            (user_id, True)
        ).fetchall()
    return [dict(f) for f in filas]

def desactivar_gasto_fijo(user_id, id):
    with get_db() as conn:
        conn.execute(
            "UPDATE config_gastos_fijos SET activo = ? WHERE id = ? AND user_id = ?",
            (False, id, user_id)
        )
    st.cache_data.clear()


# ─────────────────────────────────────────
# ESTIMACIONES
# ─────────────────────────────────────────

def guardar_estimacion(user_id, concepto, promedio):
    """Crea o reactiva una estimación. Si existía desactivada la reactiva."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO config_estimaciones (user_id, concepto, promedio, activo)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, concepto) DO UPDATE SET
                promedio = excluded.promedio,
                activo   = excluded.activo
        """, (user_id, concepto, promedio, True))
    st.cache_data.clear()

@st.cache_data(ttl=600)  # Cachea las estimaciones hasta la próxima mutación
def obtener_estimaciones(user_id):
    with get_db() as conn:
        filas = conn.execute(
            "SELECT * FROM config_estimaciones WHERE user_id = ? AND activo = ?",
            (user_id, True)
        ).fetchall()
    return [dict(f) for f in filas]

def desactivar_estimacion(user_id, id):
    with get_db() as conn:
        conn.execute(
            "UPDATE config_estimaciones SET activo = ? WHERE id = ? AND user_id = ?",
            (False, id, user_id)
        )
    st.cache_data.clear()


# ─────────────────────────────────────────
# PROVISIONES
# ─────────────────────────────────────────

def guardar_provision(user_id, concepto, monto_anual):
    """Crea o reactiva una provisión. Si existía desactivada la reactiva."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO config_provisiones (user_id, concepto, monto_anual, activo)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, concepto) DO UPDATE SET
                monto_anual = excluded.monto_anual,
                activo      = excluded.activo
        """, (user_id, concepto, monto_anual, True))
    st.cache_data.clear()

@st.cache_data(ttl=600)  # Cachea las provisiones anuales para uso en cálculo mensual
def obtener_provisiones(user_id):
    with get_db() as conn:
        filas = conn.execute(
            "SELECT * FROM config_provisiones WHERE user_id = ? AND activo = ?",
            (user_id, True)
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
            "UPDATE config_provisiones SET activo = ? WHERE id = ? AND user_id = ?",
            (False, id, user_id)
        )
    st.cache_data.clear()