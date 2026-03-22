"""
graficos.py — Visualizaciones con Plotly

Recibe datos ya calculados de calculos.py
y devuelve figuras de Plotly listas para
mostrar en Streamlit con st.plotly_chart().

"""

import plotly.graph_objects as go
import plotly.express as px

# Paleta de colores consistente en toda la app
COLORES = {
    "ahorro":      "#22c55e",   
    "ocio":        "#a78bfa",   
    "fijo":        "#60a5fa",   
    "estimacion":  "#fb923c",   
    "provision":   "#f472b6",   
    "ingresos":    "#34d399",   
    "gastos":      "#f87171",   
    "ok":          "#22c55e",
    "alerta":      "#fbbf24",
    "excedido":    "#ef4444",
}


# ─────────────────────────────────────────
# GRÁFICO DE BOLSILLOS — barras horizontales
# ─────────────────────────────────────────

def grafico_bolsillos(bolsillos: list) -> go.Figure:
    
    if not bolsillos:
        return _figura_vacia("Sin bolsillos este mes")

    nombres   = [b["nombre"]   for b in bolsillos]
    asignados = [b["asignado"] for b in bolsillos]
    gastados  = [b["gastado"]  for b in bolsillos]
    estados   = [b.get("estado", "ok") for b in bolsillos]

    colores_barras = [COLORES.get(e, COLORES["ok"]) for e in estados]

    fig = go.Figure()

    # Barra de fondo — asignado total
    fig.add_trace(go.Bar(
        name="Asignado",
        y=nombres,
        x=asignados,
        orientation="h",
        marker_color="rgba(100,100,100,0.15)",
        showlegend=True,
    ))

    # Barra de progreso — gastado
    fig.add_trace(go.Bar(
        name="Gastado",
        y=nombres,
        x=gastados,
        orientation="h",
        marker_color=colores_barras,
        showlegend=True,
    ))

    fig.update_layout(
        barmode="overlay",
        title="Estado de bolsillos",
        xaxis_title="Euros (€)",
        yaxis_title=None,
        height=max(300, len(bolsillos) * 55),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────
# GRÁFICO DE TORTA — distribución de gastos
# ─────────────────────────────────────────

def grafico_distribucion_gastos(distribucion: list) -> go.Figure:
    """
    Gráfico de torta con la distribución de gastos
    por categoría del mes.

    Recibe la salida de calculos.distribucion_gastos().
    """
    if not distribucion:
        return _figura_vacia("Sin gastos registrados este mes")

    labels  = [d["categoria"] for d in distribucion]
    values  = [d["total"]     for d in distribucion]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,           # gráfico de dona
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>€%{value:.2f}<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        title="Distribución de gastos",
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=True,
        legend=dict(orientation="v", x=1.05),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────
# GRÁFICO DE BARRAS — ingresos vs gastos anual
# ─────────────────────────────────────────

def grafico_historico_anual(historico: list) -> go.Figure:
    """
    Barras agrupadas por mes mostrando ingresos vs gastos.
    Línea adicional con el ahorro mensual.

    Recibe la salida de calculos.historico_anual().
    """
    if not historico:
        return _figura_vacia("Sin datos anuales")

    meses    = [h["mes"]      for h in historico]
    ingresos = [h["ingresos"] for h in historico]
    gastos   = [h["gastos"]   for h in historico]
    ahorros  = [h["ahorro"]   for h in historico]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Ingresos",
        x=meses,
        y=ingresos,
        marker_color=COLORES["ingresos"],
        hovertemplate="Ingresos: €%{y:.2f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        name="Gastos",
        x=meses,
        y=gastos,
        marker_color=COLORES["gastos"],
        hovertemplate="Gastos: €%{y:.2f}<extra></extra>",
    ))

    # Línea de ahorro sobre las barras
    fig.add_trace(go.Scatter(
        name="Ahorro",
        x=meses,
        y=ahorros,
        mode="lines+markers",
        line=dict(color=COLORES["ahorro"], width=2.5),
        marker=dict(size=6),
        hovertemplate="Ahorro: €%{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        title="Ingresos vs Gastos — año completo",
        xaxis_title="Mes",
        yaxis_title="Euros (€)",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────
# GRÁFICO DE LÍNEA — proyección de ahorro
# ─────────────────────────────────────────

def grafico_proyeccion_ahorro(proyeccion_data: dict) -> go.Figure:
    """
    Línea de proyección del ahorro acumulado
    para los próximos N meses.

    Recibe la salida de calculos.proyeccion_ahorro().
    """
    proyeccion = proyeccion_data.get("proyeccion", [])
    acumulado  = proyeccion_data.get("acumulado_actual", 0)
    promedio   = proyeccion_data.get("promedio_mensual", 0)

    if not proyeccion:
        return _figura_vacia("Sin datos suficientes para proyectar")

    meses  = [0]  + [p["mes"]   for p in proyeccion]
    totales= [acumulado] + [p["total"] for p in proyeccion]

    fig = go.Figure()

    # Área bajo la línea
    fig.add_trace(go.Scatter(
        name="Ahorro proyectado",
        x=meses,
        y=totales,
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(34,197,94,0.15)",
        line=dict(color=COLORES["ahorro"], width=2.5),
        marker=dict(size=5),
        hovertemplate="Mes %{x}: €%{y:.2f}<extra></extra>",
    ))

    # Línea horizontal de referencia en el punto actual
    fig.add_hline(
        y=acumulado,
        line_dash="dot",
        line_color="rgba(100,100,100,0.4)",
        annotation_text=f"Hoy: €{acumulado:.0f}",
        annotation_position="right",
    )

    fig.update_layout(
        title=f"Proyección de ahorro — promedio €{promedio:.0f}/mes",
        xaxis_title="Meses desde hoy",
        yaxis_title="Ahorro acumulado (€)",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────
# GRÁFICO DE INDICADOR — balance del mes
# ─────────────────────────────────────────

def grafico_balance(balance: float, ing_total: float) -> go.Figure:
    """
    Indicador visual tipo velocímetro mostrando
    el balance del mes como porcentaje del ingreso total.

    Verde si positivo, rojo si negativo.
    """
    if ing_total == 0:
        return _figura_vacia("Sin ingresos registrados")

    pct = round((balance / ing_total) * 100, 1)
    color = COLORES["ahorro"] if balance >= 0 else COLORES["excedido"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=balance,
        number=dict(prefix="€", valueformat=".2f"),
        delta=dict(
            reference=0,
            valueformat=".2f",
            prefix="€",
        ),
        gauge=dict(
            axis=dict(range=[-ing_total, ing_total]),
            bar=dict(color=color),
            steps=[
                dict(range=[-ing_total, 0],        color="rgba(239,68,68,0.1)"),
                dict(range=[0, ing_total * 0.3],   color="rgba(251,191,36,0.1)"),
                dict(range=[ing_total * 0.3, ing_total], color="rgba(34,197,94,0.1)"),
            ],
            threshold=dict(
                line=dict(color="white", width=2),
                thickness=0.75,
                value=0,
            ),
        ),
        title=dict(text=f"Balance del mes ({pct}% del ingreso)"),
    ))

    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────
# GRÁFICO DE INGRESOS — sueldo vs extras
# ─────────────────────────────────────────

def grafico_ingresos(ing_sueldo: float, ing_extras: float) -> go.Figure:
    """
    Gráfico de torta simple mostrando la proporción
    entre sueldo e ingresos extra del mes.
    """
    if ing_sueldo == 0 and ing_extras == 0:
        return _figura_vacia("Sin ingresos este mes")

    fig = go.Figure(go.Pie(
        labels=["Sueldo", "Extras"],
        values=[ing_sueldo, ing_extras],
        hole=0.5,
        marker_colors=[COLORES["fijo"], COLORES["estimacion"]],
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>€%{value:.2f}<extra></extra>",
    ))

    fig.update_layout(
        title="Composición de ingresos",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────
# UTILIDAD — figura vacía
# ─────────────────────────────────────────

def _figura_vacia(mensaje: str) -> go.Figure:
    """Devuelve una figura con un mensaje cuando no hay datos."""
    fig = go.Figure()
    fig.add_annotation(
        text=mensaje,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray"),
    )
    fig.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig