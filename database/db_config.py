import streamlit as st
from .db_core import get_db


def _parse_mes(mes: str) -> tuple[int, int]:
    anio_txt, mes_txt = mes.split("-", 1)
    return int(anio_txt), int(mes_txt)


def _format_mes(anio: int, mes: int) -> str:
    return f"{anio:04d}-{mes:02d}"


def _sumar_meses(mes: str, cantidad: int) -> str:
    anio, mes_num = _parse_mes(mes)
    total = (anio * 12) + (mes_num - 1) + cantidad
    nuevo_anio, nuevo_mes_idx = divmod(total, 12)
    return _format_mes(nuevo_anio, nuevo_mes_idx + 1)


def _meses_entre(inicio: str, fin: str) -> int:
    anio_inicio, mes_inicio = _parse_mes(inicio)
    anio_fin, mes_fin = _parse_mes(fin)
    return (anio_fin - anio_inicio) * 12 + (mes_fin - mes_inicio)


def _cuota_plazo(monto_total: float, meses: int, indice_mes: int) -> float:
    cuota_base = round(float(monto_total) / int(meses), 2)
    if indice_mes < int(meses) - 1:
        return cuota_base
    acumulado = round(cuota_base * (int(meses) - 1), 2)
    return round(float(monto_total) - acumulado, 2)


def _enriquecer_plazo(plazo: dict, mes_referencia: str | None = None) -> dict:
    plazo["mes_final"] = _sumar_meses(plazo["inicio_mes"], int(plazo["meses"]) - 1)
    plazo["cuota_base"] = round(float(plazo["monto_total"]) / int(plazo["meses"]), 2)

    if mes_referencia is not None and plazo["inicio_mes"] <= mes_referencia <= plazo["mes_final"]:
        indice_mes = _meses_entre(plazo["inicio_mes"], mes_referencia)
        plazo["cuota_mes"] = _cuota_plazo(plazo["monto_total"], plazo["meses"], indice_mes)
        plazo["activo_en_mes"] = True
        plazo["meses_restantes"] = int(plazo["meses"]) - indice_mes
    else:
        plazo["cuota_mes"] = plazo["cuota_base"]
        plazo["activo_en_mes"] = False if mes_referencia is not None else True
        plazo["meses_restantes"] = (
            int(plazo["meses"])
            if mes_referencia is None or mes_referencia < plazo["inicio_mes"]
            else 0
        )
    return plazo

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
# PROVISIONES (legado sin uso)
# ─────────────────────────────────────────

def guardar_provision(*_args, **_kwargs):
    raise RuntimeError("guardar_provision ya no se usa. Usa guardar_plazo.")


def obtener_provisiones(*_args, **_kwargs):
    return []


def desactivar_provision(*_args, **_kwargs):
    return None


def guardar_plazo(user_id, concepto, monto_total, meses, inicio_mes):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO config_plazos (user_id, concepto, monto_total, meses, inicio_mes, activo)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, concepto, inicio_mes) DO UPDATE SET
                monto_total = excluded.monto_total,
                meses       = excluded.meses,
                activo      = excluded.activo
            """,
            (user_id, concepto, monto_total, meses, inicio_mes, True),
        )
    st.cache_data.clear()


@st.cache_data(ttl=600)
def obtener_plazos(user_id, mes=None):
    with get_db() as conn:
        filas = conn.execute(
            "SELECT * FROM config_plazos WHERE user_id = ? AND activo = ? ORDER BY inicio_mes ASC, concepto ASC",
            (user_id, True),
        ).fetchall()
    resultado = [_enriquecer_plazo(dict(f), mes) for f in filas]
    if mes is not None:
        resultado = [plazo for plazo in resultado if plazo["activo_en_mes"]]
    return resultado


def desactivar_plazo(user_id, plazo_id):
    with get_db() as conn:
        conn.execute(
            "UPDATE config_plazos SET activo = ? WHERE id = ? AND user_id = ?",
            (False, plazo_id, user_id),
        )
    st.cache_data.clear()
