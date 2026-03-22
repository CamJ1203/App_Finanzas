from .db_core import get_db

def guardar_ingreso_sueldo(user_id, fecha, concepto, monto):
    _guardar(user_id, fecha, concepto, monto, "sueldo")

def guardar_ingreso_extra(user_id, fecha, concepto, monto):
    _guardar(user_id, fecha, concepto, monto, "extra")

def _guardar(user_id, fecha, concepto, monto, tipo):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ingresos (user_id, fecha, concepto, monto, tipo) VALUES (?,?,?,?,?)",
            (user_id, fecha, concepto, monto, tipo)
        )

def obtener_ingresos(user_id, mes=None):
    query  = "SELECT * FROM ingresos WHERE user_id = ?"
    params = [user_id]
    if mes:
        query  += " AND fecha LIKE ?"
        params.append(f"{mes}%")
    query += " ORDER BY fecha DESC"
    with get_db() as conn:
        filas = conn.execute(query, params).fetchall()
    return [dict(f) for f in filas]

def total_ingresos(user_id, mes):
    return _sumar(user_id, mes, None)

def total_sueldo(user_id, mes):
    return _sumar(user_id, mes, "sueldo")

def total_extras(user_id, mes):
    return _sumar(user_id, mes, "extra")

def _sumar(user_id, mes, tipo):
    query  = "SELECT SUM(monto) FROM ingresos WHERE user_id = ? AND fecha LIKE ?"
    params = [user_id, f"{mes}%"]
    if tipo:
        query  += " AND tipo = ?"
        params.append(tipo)
    with get_db() as conn:
        resultado = conn.execute(query, params).fetchone()[0]
    return resultado or 0

def borrar_ingreso(id):
    with get_db() as conn:
        conn.execute("DELETE FROM ingresos WHERE id = ?", (id,))