import streamlit as st
from database import (
    obtener_metricas_agrupadas,
    obtener_totales_configurables,
    obtener_pct_ahorro,
    obtener_ingresos,
    obtener_gastos_fijos,
    obtener_estimaciones,
    obtener_provisiones,
    obtener_gastos_importantes,
    obtener_gastos_casa,
    obtener_gastos_generales,
)


_DEFAULT_ROW = {
    "ingresos": 0.0,
    "ocio": 0.0,
    "casa": 0.0,
    "imprevistos": 0.0,
}


def _row_for_mes(mes: str, metricas: dict[str, dict[str, float]]) -> dict[str, float]:
    return metricas.get(mes, _DEFAULT_ROW)


@st.cache_data(ttl=600)
def calcular_mes(user_id: int, mes: str) -> dict[str, float]:
    anio = int(mes.split("-", 1)[0])
    metricas = obtener_metricas_agrupadas(user_id, anio=anio)
    config = obtener_totales_configurables(user_id)
    totals = _row_for_mes(mes, metricas)

    ingresos = totals["ingresos"]
    ing_sueldo = totals.get("ing_sueldo", 0.0)
    ing_extras = totals.get("ing_extras", 0.0)
    total_previstos = round(
        config["fijos"] + config["estimaciones"] + config["provisiones"], 2
    )
    remanente = round(int(ingresos - total_previstos), 2)

    pct_ahorro, pct_ocio = obtener_pct_ahorro(user_id)
    ahorro_previsto = round(remanente * pct_ahorro, 2)
    ocio_previsto = round(remanente * pct_ocio, 2)

    total_casa = totals["casa"]
    total_imprevistos = totals["imprevistos"]
    total_ocio_gastado = totals["ocio"]

    ahorro_real = round(((ingresos - total_casa) * pct_ahorro) - total_imprevistos, 2)
    ocio_disponible = round(((ingresos - total_casa) * pct_ocio) - total_ocio_gastado, 2)
    sobrante_previstos = round(total_previstos - total_casa, 2)

    return {
        "ing_total": ingresos,
        "ing_sueldo": ing_sueldo,
        "ing_extras": ing_extras,
        "total_previstos": total_previstos,
        "detalle_fijos": obtener_gastos_fijos(user_id),
        "detalle_estim": obtener_estimaciones(user_id),
        "detalle_provis": obtener_provisiones(user_id),
        "remanente": remanente,
        "pct_ahorro": pct_ahorro,
        "pct_ocio": pct_ocio,
        "ahorro_previsto": ahorro_previsto,
        "ocio_previsto": ocio_previsto,
        "total_imprevistos": total_imprevistos,
        "gastos_imp_lista": obtener_gastos_importantes(user_id, mes),
        "reduccion_ahorro": round(total_imprevistos * pct_ahorro, 2),
        "reduccion_ocio": round(total_imprevistos * pct_ocio, 2),
        "ahorro_real": ahorro_real,
        "ocio_disponible": ocio_disponible,
        "total_ocio_gastado": total_ocio_gastado,
        "total_casa_gastado": total_casa,
        "gastos_casa_lista": obtener_gastos_casa(user_id, mes),
        "sobrante_previstos": sobrante_previstos,
        "mes": mes,
    }


@st.cache_data(ttl=600)
def _ahorro_total_acumulado(user_id: int) -> float:
    return obtener_resumen_global(user_id)["ahorro_total"]


@st.cache_data(ttl=600)
def _ocio_total_acumulado(user_id: int) -> float:
    return obtener_resumen_global(user_id)["ocio_total"]


@st.cache_data(ttl=600)
def obtener_resumen_global(user_id: int) -> dict[str, float]:
    metricas = obtener_metricas_agrupadas(user_id)
    pct_a, pct_o = obtener_pct_ahorro(user_id)

    ahorro_acumulado = 0.0
    ocio_acumulado = 0.0
    for row in metricas.values():
        ahorro_acumulado += round(((row["ingresos"] - row["casa"]) * pct_a) - row["imprevistos"], 2)
        ocio_base = round((row["ingresos"] - row["casa"]) * pct_o, 2)
        ocio_acumulado += round(ocio_base - row["ocio"], 2)

    return {
        "ahorro_total": round(ahorro_acumulado, 2),
        "ocio_total": round(ocio_acumulado, 2),
    }


@st.cache_data(ttl=600)
def historico_anual(user_id: int, anio: int) -> list[dict[str, float]]:
    metricas = obtener_metricas_agrupadas(user_id, anio=anio)
    pct_a, _ = obtener_pct_ahorro(user_id)

    nombre_meses = [
        "Ene","Feb","Mar","Abr","May","Jun",
        "Jul","Ago","Sep","Oct","Nov","Dic",
    ]

    resultado: list[dict[str, float]] = []
    for indice, nombre in enumerate(nombre_meses, start=1):
        mes = f"{anio}-{indice:02d}"
        fila = metricas.get(mes)
        if not fila:
            continue

        ahorro = round(((fila["ingresos"] - fila["casa"]) * pct_a) - fila["imprevistos"], 2)
        resultado.append({
            "mes": nombre,
            "ingresos": fila["ingresos"],
            "previstos": fila["casa"] + fila["ocio"] + fila["imprevistos"],
            "imprevistos": fila["imprevistos"],
            "ocio_gast": fila["ocio"],
            "ahorro": ahorro,
        })

    return resultado


@st.cache_data(ttl=600)
def obtener_dashboard_contexto(user_id: int, mes: str, anio: int) -> dict[str, object]:
    ingresos = obtener_ingresos(user_id, mes)
    gastos_ocio = obtener_gastos_generales(user_id, mes)
    d_mes = calcular_mes(user_id, mes)

    todos: list[dict[str, object]] = []
    for item in ingresos:
        todos.append({
            "_orden": item.get("creado_en") or f"{item['fecha']} 00:00:00.000",
            "fecha": item["fecha"],
            "tipo": "Ingreso",
            "concepto": item["concepto"],
            "monto": item["monto"],
        })
    for item in gastos_ocio:
        todos.append({
            "_orden": item.get("creado_en") or f"{item['fecha']} 00:00:00.000",
            "fecha": item["fecha"],
            "tipo": "Ocio",
            "concepto": item["concepto"],
            "monto": -item["monto"],
        })
    for item in d_mes["gastos_imp_lista"]:
        todos.append({
            "_orden": item.get("creado_en") or f"{item['fecha']} 00:00:00.000",
            "fecha": item["fecha"],
            "tipo": "Imprevisto",
            "concepto": item["concepto"],
            "monto": -item["monto"],
        })
    for item in d_mes["gastos_casa_lista"]:
        todos.append({
            "_orden": item.get("creado_en") or f"{item['fecha']} 00:00:00.000",
            "fecha": item["fecha"],
            "tipo": "Gastos fijos",
            "concepto": item["concepto"],
            "monto": -item["monto"],
        })

    return {
        "resumen_global": obtener_resumen_global(user_id),
        "mes": d_mes,
        "hist": historico_anual(user_id, anio),
        "ingresos": ingresos,
        "gastos_ocio": gastos_ocio,
        "todos": [
            {
                "fecha": item["fecha"],
                "tipo": item["tipo"],
                "concepto": item["concepto"],
                "monto": item["monto"],
            }
            for item in sorted(todos, key=lambda x: (x["_orden"], x["fecha"]), reverse=True)
        ],
        "totales_historial": {
            "ingresos": round(sum(item["monto"] for item in ingresos), 2),
            "ocio": round(sum(item["monto"] for item in gastos_ocio), 2),
            "imprevistos": round(sum(item["monto"] for item in d_mes["gastos_imp_lista"]), 2),
            "casa": round(sum(item["monto"] for item in d_mes["gastos_casa_lista"]), 2),
        },
    }
