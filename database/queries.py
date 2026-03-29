import streamlit as st
from .db_core import get_db


def _build_date_range(anio: int | None) -> tuple[str | None, str | None]:
    if anio is None:
        return None, None

    inicio = f"{anio}-01-01"
    fin = f"{anio + 1}-01-01"
    return inicio, fin


@st.cache_data(ttl=600)
def obtener_metricas_agrupadas(user_id: int, anio: int | None = None) -> dict[str, dict[str, float]]:
    """Devuelve totales mensuales agregados por categoría.

    Las consultas se agrupan usando substr(fecha, 1, 7) y UNION ALL para
    evitar múltiples barridos de la base de datos.
    """
    start, end = _build_date_range(anio)
    where_clause = "WHERE user_id = ?"
    params = [user_id]
    if start is not None and end is not None:
        where_clause += " AND fecha >= ? AND fecha < ?"
        params.extend([start, end])

    query = f"""
        SELECT mes,
               SUM(ingresos) AS ingresos,
               SUM(ing_sueldo) AS ing_sueldo,
               SUM(ing_extras) AS ing_extras,
               SUM(ocio) AS ocio,
               SUM(casa) AS casa,
               SUM(imprevistos) AS imprevistos
        FROM (
            SELECT substr(fecha,1,7) AS mes,
                   monto AS ingresos,
                   CASE WHEN tipo = 'sueldo' THEN monto ELSE 0.0 END AS ing_sueldo,
                   CASE WHEN tipo = 'extra' THEN monto ELSE 0.0 END AS ing_extras,
                   0.0 AS ocio,
                   0.0 AS casa,
                   0.0 AS imprevistos
            FROM ingresos
            {where_clause}
            UNION ALL
            SELECT substr(fecha,1,7) AS mes,
                   0.0 AS ingresos,
                   0.0 AS ing_sueldo,
                   0.0 AS ing_extras,
                   monto AS ocio,
                   0.0 AS casa,
                   0.0 AS imprevistos
            FROM gastos_generales
            {where_clause}
            UNION ALL
            SELECT substr(fecha,1,7) AS mes,
                   0.0 AS ingresos,
                   0.0 AS ing_sueldo,
                   0.0 AS ing_extras,
                   0.0 AS ocio,
                   monto AS casa,
                   0.0 AS imprevistos
            FROM gastos_casa
            {where_clause}
            UNION ALL
            SELECT substr(fecha,1,7) AS mes,
                   0.0 AS ingresos,
                   0.0 AS ing_sueldo,
                   0.0 AS ing_extras,
                   0.0 AS ocio,
                   0.0 AS casa,
                   monto AS imprevistos
            FROM gastos_importantes
            {where_clause}
        ) agrupadas
        GROUP BY mes
        ORDER BY mes
    """

    with get_db() as conn:
        filas = conn.execute(query, tuple(params * 4)).fetchall()

    resultado: dict[str, dict[str, float]] = {}
    for fila in filas:
        datos = dict(fila)
        resultado[datos["mes"]] = {
            "ingresos": float(datos.get("ingresos", 0) or 0),
            "ing_sueldo": float(datos.get("ing_sueldo", 0) or 0),
            "ing_extras": float(datos.get("ing_extras", 0) or 0),
            "ocio": float(datos.get("ocio", 0) or 0),
            "casa": float(datos.get("casa", 0) or 0),
            "imprevistos": float(datos.get("imprevistos", 0) or 0),
        }

    return resultado


@st.cache_data(ttl=600)
def obtener_totales_configurables(user_id: int) -> dict[str, float]:
    """Devuelve los totales mensuales de gastos configurados."""
    with get_db() as conn:
        fila_fijos = conn.execute(
            "SELECT SUM(monto) AS total FROM config_gastos_fijos WHERE user_id = ? AND activo = ?",
            (user_id, True),
        ).fetchone()
        fila_estim = conn.execute(
            "SELECT SUM(promedio) AS total FROM config_estimaciones WHERE user_id = ? AND activo = ?",
            (user_id, True),
        ).fetchone()
        fila_prov = conn.execute(
            "SELECT SUM(monto_anual) AS total FROM config_provisiones WHERE user_id = ? AND activo = ?",
            (user_id, True),
        ).fetchone()

    fijos = float((fila_fijos and next(iter(fila_fijos.values()))) or 0)
    estimaciones = float((fila_estim and next(iter(fila_estim.values()))) or 0)
    provisiones = float((fila_prov and next(iter(fila_prov.values()))) or 0) / 12

    return {
        "fijos": fijos,
        "estimaciones": estimaciones,
        "provisiones": round(provisiones, 2),
    }
