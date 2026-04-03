from datetime import datetime
import streamlit as st
from .db_core import get_db


def _timestamp_actual():
    return datetime.now().isoformat(timespec="milliseconds")

def guardar_ingreso_sueldo(user_id, fecha, concepto, monto):
    _guardar(user_id, fecha, concepto, monto, "sueldo")

def guardar_ingreso_extra(user_id, fecha, concepto, monto):
    _guardar(user_id, fecha, concepto, monto, "extra")

def _guardar(user_id, fecha, concepto, monto, tipo):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ingresos (user_id, fecha, concepto, monto, tipo, creado_en) VALUES (?,?,?,?,?,?)",
            (user_id, fecha, concepto, monto, tipo, _timestamp_actual())
        )
    # Invalida solo después de escribir; el cache de lectura permanece válido hasta que hay cambios.
    st.cache_data.clear()

@st.cache_data(ttl=600)  # Lectura cacheada, 10 minutos
def obtener_ingresos(user_id, mes=None):
    query  = "SELECT * FROM ingresos WHERE user_id = ?"
    params = [user_id]
    if mes:
        query  += " AND fecha LIKE ?"
        params.append(f"{mes}%")
    query += " ORDER BY creado_en DESC, fecha DESC, id DESC"
    with get_db() as conn:
        filas = conn.execute(query, params).fetchall()
    return [dict(f) for f in filas]

def total_ingresos(user_id, mes):
    return _sumar(user_id, mes, None)

def total_sueldo(user_id, mes):
    return _sumar(user_id, mes, "sueldo")

def total_extras(user_id, mes):
    return _sumar(user_id, mes, "extra")

@st.cache_data(ttl=600)  # Agrega en SQL y cachea el total de ingresos
def _sumar(user_id, mes, tipo):
    query  = "SELECT SUM(monto) FROM ingresos WHERE user_id = ? AND fecha LIKE ?"
    params = [user_id, f"{mes}%"]
    if tipo:
        query  += " AND tipo = ?"
        params.append(tipo)
    with get_db() as conn:
        fila = conn.execute(query, params).fetchone()
    if not fila:
        return 0
    if isinstance(fila, dict):
        resultado = next(iter(fila.values()))
    else:
        resultado = fila[0]
    return resultado or 0

@st.cache_data(ttl=600)
def obtener_ingresos_resumen(user_id, mes):
    with get_db() as conn:
        fila = conn.execute(
            "SELECT SUM(monto) AS total,"
            " SUM(CASE WHEN tipo = 'sueldo' THEN monto ELSE 0 END) AS sueldo,"
            " SUM(CASE WHEN tipo = 'extra' THEN monto ELSE 0 END) AS extras"
            " FROM ingresos WHERE user_id = ? AND fecha LIKE ?",
            (user_id, f"{mes}%")
        ).fetchone()
    if not fila:
        return 0, 0, 0
    if isinstance(fila, dict):
        return fila["total"] or 0, fila["sueldo"] or 0, fila["extras"] or 0
    return fila[0] or 0, fila[1] or 0, fila[2] or 0

@st.cache_data(ttl=600)
def obtener_ingresos_por_mes(user_id, anio=None):
    query  = "SELECT substr(fecha,1,7) AS mes, SUM(monto) AS total,"
    query += " SUM(CASE WHEN tipo = 'sueldo' THEN monto ELSE 0 END) AS sueldo,"
    query += " SUM(CASE WHEN tipo = 'extra' THEN monto ELSE 0 END) AS extras"
    query += " FROM ingresos WHERE user_id = ?"
    params = [user_id]
    if anio is not None:
        query += " AND fecha LIKE ?"
        params.append(f"{anio}-%")
    query += " GROUP BY mes ORDER BY mes ASC"
    with get_db() as conn:
        filas = conn.execute(query, params).fetchall()
    resultado = {}
    for f in filas:
        resultado[f["mes"]] = {
            "total": f["total"] or 0,
            "sueldo": f["sueldo"] or 0,
            "extras": f["extras"] or 0,
        }
    return resultado

def borrar_ingreso(id):
    with get_db() as conn:
        conn.execute("DELETE FROM ingresos WHERE id = ?", (id,))
    st.cache_data.clear()
