#Cambie el nombre de Gastos casa a Gastos fijos, ya que es más representativo de lo que realmente son, y permite incluir otros gastos previstos que no sean solo de casa. 
#las variables no las toque asi que tomar en cuenta.
from datetime import datetime
import streamlit as st
from .db_core import get_db


def _timestamp_actual():
    return datetime.now().isoformat(timespec="milliseconds")

# ─────────────────────────────────────────
# GASTOS GENERALES (ocio)
# ─────────────────────────────────────────

def guardar_gasto_general(user_id, fecha, concepto, monto, categoria):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO gastos_generales (user_id, fecha, concepto, monto, categoria, creado_en)"
            " VALUES (?,?,?,?,?,?)",
            (user_id, fecha, concepto, monto, categoria, _timestamp_actual())
        )
    # Solo limpiar cache cuando hay una mutación de datos.
    st.cache_data.clear()

def obtener_gastos_generales(user_id, mes=None):
    return _consultar("gastos_generales", user_id, mes)

@st.cache_data(ttl=600)
def total_gastos_generales(user_id, mes):
    """Total de gastos de ocio por mes, calculado en SQL."""
    with get_db() as conn:
        fila = conn.execute(
            "SELECT SUM(monto) AS total FROM gastos_generales"
            " WHERE user_id = ? AND fecha LIKE ?",
            (user_id, f"{mes}%"),
        ).fetchone()
    if not fila:
        return 0
    if isinstance(fila, dict):
        return fila["total"] or 0
    return fila[0] or 0


def borrar_gasto_general(id):
    _borrar("gastos_generales", id)
    st.cache_data.clear()


# ─────────────────────────────────────────
# GASTOS FIJOS
# ─────────────────────────────────────────

def guardar_gasto_casa(user_id, fecha, concepto, monto, recurrente=False):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO gastos_casa (user_id, fecha, concepto, monto, recurrente, creado_en)"
            " VALUES (?,?,?,?,?,?)",
            (user_id, fecha, concepto, monto, bool(recurrente), _timestamp_actual())
        )
    st.cache_data.clear()

def obtener_gastos_casa(user_id, mes=None):
    return _consultar("gastos_casa", user_id, mes)

@st.cache_data(ttl=600)
def total_gastos_casa(user_id, mes):
    """Total de gastos fijos por mes, calculado en SQL."""
    with get_db() as conn:
        fila = conn.execute(
            "SELECT SUM(monto) AS total FROM gastos_casa"
            " WHERE user_id = ? AND fecha LIKE ?",
            (user_id, f"{mes}%"),
        ).fetchone()
    if not fila:
        return 0
    if isinstance(fila, dict):
        return fila["total"] or 0
    return fila[0] or 0


def borrar_gasto_casa(id):
    _borrar("gastos_casa", id)
    st.cache_data.clear()


# ─────────────────────────────────────────
# GASTOS IMPORTANTES (imprevistos)
# ─────────────────────────────────────────

def guardar_gasto_importante(user_id, fecha, concepto, monto, prioridad="media"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO gastos_importantes (user_id, fecha, concepto, monto, prioridad, creado_en)"
            " VALUES (?,?,?,?,?,?)",
            (user_id, fecha, concepto, monto, prioridad, _timestamp_actual())
        )
    st.cache_data.clear()

def obtener_gastos_importantes(user_id, mes=None):
    return _consultar("gastos_importantes", user_id, mes)

def borrar_gasto_importante(id):
    _borrar("gastos_importantes", id)
    st.cache_data.clear()

@st.cache_data(ttl=600)  # Agregación SQL de gastos importantes por mes
def total_gastos_importantes(user_id, mes):
    with get_db() as conn:
        fila = conn.execute(
            "SELECT SUM(monto) FROM gastos_importantes WHERE user_id=? AND fecha LIKE ?",
            (user_id, f"{mes}%")
        ).fetchone()
    if not fila:
        return 0
    if isinstance(fila, dict):
        resultado = next(iter(fila.values()))
    else:
        resultado = fila[0]
    return resultado or 0


@st.cache_data(ttl=600)  # Lectura agregada por mes para cada tabla de gastos
def _sumar_por_mes(tabla, user_id, anio=None):
    query  = f"SELECT substr(fecha,1,7) AS mes, SUM(monto) AS total"
    query += f" FROM {tabla} WHERE user_id = ?"
    params = [user_id]
    if anio is not None:
        query += " AND fecha LIKE ?"
        params.append(f"{anio}-%")
    query += " GROUP BY mes ORDER BY mes ASC"
    with get_db() as conn:
        filas = conn.execute(query, params).fetchall()
    return {f["mes"]: f["total"] or 0 for f in filas}


def obtener_gastos_generales_por_mes(user_id, anio=None):
    return _sumar_por_mes("gastos_generales", user_id, anio)


def obtener_gastos_casa_por_mes(user_id, anio=None):
    return _sumar_por_mes("gastos_casa", user_id, anio)


def obtener_gastos_importantes_por_mes(user_id, anio=None):
    return _sumar_por_mes("gastos_importantes", user_id, anio)


# ─────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────

@st.cache_data(ttl=600)  # Cache de detalles por mes
def _consultar(tabla, user_id, mes):
    query  = f"SELECT * FROM {tabla} WHERE user_id = ?"
    params = [user_id]
    if mes:
        query  += " AND fecha LIKE ?"
        params.append(f"{mes}%")
    query += " ORDER BY creado_en DESC, fecha DESC, id DESC"
    with get_db() as conn:
        filas = conn.execute(query, params).fetchall()
    return [dict(f) for f in filas]

def _borrar(tabla, id):
    with get_db() as conn:
        conn.execute(f"DELETE FROM {tabla} WHERE id = ?", (id,))
