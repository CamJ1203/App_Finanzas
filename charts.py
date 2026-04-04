import streamlit as st


def _filtrar_datos_pastel(etiquetas, valores):
    datos = []
    for etiqueta, valor in zip(etiquetas, valores):
        if valor is not None and valor >= 0:
            datos.append({"categoria": etiqueta, "monto": round(float(valor), 2)})
    return datos


def _color_categoria(categoria: str) -> str:
    colores = {
        "Gastos fijos": "#4E79A7",
        "Fixed expenses": "#4E79A7",
        "Ocio": "#F28E2B",
        "Fun": "#F28E2B",
        "Imprevistos": "#E15759",
        "Unexpected": "#E15759",
        "Sueldo": "#59A14F",
        "Salary": "#59A14F",
        "Extras": "#76B7B2",
        "Extra": "#76B7B2",
    }
    return colores.get(categoria, "#9C755F")


def _render_legend(datos):
    items = []
    for item in datos:
        items.append(
            (
                "<span style=\"display:inline-flex;align-items:center;"
                "margin:0 14px 8px 0;font-size:0.92rem;white-space:nowrap;\">"
                f"<span style=\"width:12px;height:12px;border-radius:999px;"
                f"background:{item['color']};display:inline-block;margin-right:8px;\"></span>"
                f"{item['categoria']} - €{item['monto']:,.2f}"
                "</span>"
            )
        )

    st.markdown(
        (
            "<div style=\"display:flex;flex-wrap:wrap;justify-content:center;"
            "margin-top:2px;\">"
            + "".join(items)
            + "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_torta(*args, height: int = 250):
    if len(args) == 2:
        etiquetas, valores = args
    elif len(args) == 3:
        _, etiquetas, valores = args
    else:
        raise ValueError("render_torta espera etiquetas y valores.")

    datos = _filtrar_datos_pastel(etiquetas, valores)

    if not any(item["monto"] > 0 for item in datos):
        st.info("No hay datos para mostrar en esta grafica.")
        return

    datos = [
        {
            **item,
            "color": _color_categoria(item["categoria"]),
            "sombra": "#00000030",
        }
        for item in datos
    ]

    spec = {
        "layer": [
            {
                "mark": {
                    "type": "arc",
                    "innerRadius": 38,
                    "outerRadius": 102,
                    "cornerRadius": 6,
                    "opacity": 0.18,
                },
                "encoding": {
                    "theta": {"field": "monto", "type": "quantitative"},
                    "color": {
                        "field": "sombra",
                        "type": "nominal",
                        "scale": None,
                        "legend": None,
                    },
                },
            },
            {
                "mark": {
                    "type": "arc",
                    "innerRadius": 42,
                    "outerRadius": 96,
                    "cornerRadius": 8,
                    "stroke": "#FFFFFF",
                    "strokeWidth": 2,
                },
                "encoding": {
                    "theta": {"field": "monto", "type": "quantitative"},
                    "color": {
                        "field": "color",
                        "type": "nominal",
                        "scale": None,
                        "legend": None,
                    },
                    "tooltip": [
                        {"field": "categoria", "type": "nominal", "title": "Tipo"},
                        {"field": "monto", "type": "quantitative", "title": "Monto", "format": ",.2f"},
                    ],
                },
            },
        ],
        "view": {"stroke": None},
        "config": {"background": None},
    }

    st.vega_lite_chart(datos, spec, width="stretch", height=height)
    _render_legend(datos)
