import streamlit as st


def _filtrar_datos_pastel(etiquetas, valores):
    datos = []
    for etiqueta, valor in zip(etiquetas, valores):
        if valor and valor > 0:
            datos.append({"categoria": etiqueta, "monto": round(float(valor), 2)})
    return datos


def render_torta(titulo: str, etiquetas: list[str], valores: list[float], height: int = 260):
    datos = _filtrar_datos_pastel(etiquetas, valores)
    st.subheader(titulo)

    if not datos:
        st.info("No hay datos para mostrar en esta gráfica.")
        return

    spec = {
        "mark": {"type": "arc", "innerRadius": 35, "outerRadius": 100},
        "encoding": {
            "theta": {"field": "monto", "type": "quantitative"},
            "color": {
                "field": "categoria",
                "type": "nominal",
                "legend": {"title": None, "orient": "bottom"},
            },
            "tooltip": [
                {"field": "categoria", "type": "nominal", "title": "Tipo"},
                {"field": "monto", "type": "quantitative", "title": "Monto", "format": ",.2f"},
            ],
        },
        "view": {"stroke": None},
    }

    st.vega_lite_chart(datos, spec, width="stretch", height=height)
