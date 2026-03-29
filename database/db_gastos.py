from .db_core import get_db

# ─────────────────────────────────────────
# GASTOS GENERALES (ocio)
# ─────────────────────────────────────────

def guardar_gasto_general(user_id, fecha, concepto, monto, categoria):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO gastos_generales (user_id, fecha, concepto, monto, categoria)"
            " VALUES (?,?,?,?,?)",
            (user_id, fecha, concepto, monto, categoria)
        )

def obtener_gastos_generales(user_id, mes=None):
    return _consultar("gastos_generales", user_id, mes)

def borrar_gasto_general(id):
    _borrar("gastos_generales", id)


# ─────────────────────────────────────────
# GASTOS DE CASA
# ─────────────────────────────────────────

def guardar_gasto_casa(user_id, fecha, concepto, monto, recurrente=False):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO gastos_casa (user_id, fecha, concepto, monto, recurrente)"
            " VALUES (?,?,?,?,?)",
            (user_id, fecha, concepto, monto, int(recurrente))
        )

def obtener_gastos_casa(user_id, mes=None):
    return _consultar("gastos_casa", user_id, mes)

def borrar_gasto_casa(id):
    _borrar("gastos_casa", id)


# ─────────────────────────────────────────
# GASTOS IMPORTANTES (imprevistos)
# ─────────────────────────────────────────

def guardar_gasto_importante(user_id, fecha, concepto, monto, prioridad="media"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO gastos_importantes (user_id, fecha, concepto, monto, prioridad)"
            " VALUES (?,?,?,?,?)",
            (user_id, fecha, concepto, monto, prioridad)
        )

def obtener_gastos_importantes(user_id, mes=None):
    return _consultar("gastos_importantes", user_id, mes)

def borrar_gasto_importante(id):
    _borrar("gastos_importantes", id)

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


# ─────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────

def _consultar(tabla, user_id, mes):
    query  = f"SELECT * FROM {tabla} WHERE user_id = ?"
    params = [user_id]
    if mes:
        query  += " AND fecha LIKE ?"
        params.append(f"{mes}%")
    query += " ORDER BY fecha DESC"
    with get_db() as conn:
        filas = conn.execute(query, params).fetchall()
    return [dict(f) for f in filas]

def _borrar(tabla, id):
    with get_db() as conn:
        conn.execute(f"DELETE FROM {tabla} WHERE id = ?", (id,))