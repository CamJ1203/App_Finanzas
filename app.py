#NOTA: Cambie el nombre de Gastos casa a Gastos fijos, ya que es más representativo de lo que realmente son, y permite incluir otros gastos previstos que no sean solo de casa. las variables no las toque tomar en cuenta.

"""
app.py — App de Finanzas Personales
Ejecutar: streamlit run app.py
"""

import streamlit as st
import database as db
from datetime import date
import calendar

from database import (
    crear_tablas, get_db,
    guardar_ingreso_sueldo, guardar_ingreso_extra,
    obtener_ingresos, borrar_ingreso,
    guardar_gasto_general, obtener_gastos_generales, borrar_gasto_general,
    guardar_gasto_casa, obtener_gastos_casa, total_gastos_casa, borrar_gasto_casa,
    guardar_gasto_importante, obtener_gastos_importantes, total_gastos_importantes, borrar_gasto_importante,
    total_ingresos, total_sueldo, total_extras,
    guardar_gasto_fijo, obtener_gastos_fijos, desactivar_gasto_fijo,
    guardar_estimacion, obtener_estimaciones, desactivar_estimacion,
    guardar_provision, obtener_provisiones, desactivar_provision,
    actualizar_pct_ahorro,
    obtener_metricas_agrupadas, obtener_totales_configurables,
)
from auth import pantalla_auth, hay_sesion, obtener_sesion, cerrar_sesion
from logic.calculos import (
    obtener_dashboard_contexto, obtener_resumen_global,
)

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────

st.set_page_config(
    page_title="Mis Finanzas",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Esconder el widget de estado de ejecución y elementos de Streamlit */
[data-testid="stStatusWidget"] {
    display: none !important;
}
#MainMenu {
    visibility: hidden;
}
footer {
    visibility: hidden;
}
/* El header debe permanecer visible para poder abrir/cerrar la sidebar */
/* header {
    visibility: hidden;
} */
/* Tabs sticky — respeta la altura del header original para no tapar el sidebar */
.stTabs [data-baseweb="tab-list"] {
    position: sticky;
    top: 3.5rem;
    z-index: 100;
    background: var(--background-color);
    padding-bottom: 4px;
}
.block-container { padding-top: 2rem !important; }

/* FIX MÓVIL — teclado */
input[type="text"],
input[type="email"],
input[type="password"],
textarea {
    -webkit-user-select: text !important;
    user-select: text !important;
}
</style>
""", unsafe_allow_html=True)

if hasattr(st, "fragment"):
    fragment = st.fragment
else:
    def fragment(func):
        return func


# ─────────────────────────────────────────
# DB + SESIÓN
# ─────────────────────────────────────────

crear_tablas()

if not hay_sesion():
    pantalla_auth()
    st.stop()


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

@st.cache_data(ttl=600)
def mes_cerrado(user_id: int, mes: str) -> bool:
    with get_db() as conn:
        return conn.execute(
            "SELECT id FROM cierre_mes WHERE user_id=? AND mes=?",
            (user_id, mes)
        ).fetchone() is not None

def desbloquear_mes(user_id: int, mes: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM cierre_mes WHERE user_id=? AND mes=?",
            (user_id, mes)
        )
    st.cache_data.clear()

def guardar_cierre(user_id: int, mes: str, ahorro_extra: float, ocio_extra: float):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO cierre_mes (user_id, mes, ahorro_mes, sobrante_movido, ahorro_total_mes)
            VALUES (?,?,?,?,?)
            ON CONFLICT(user_id, mes) DO UPDATE SET
                ahorro_mes       = excluded.ahorro_mes,
                sobrante_movido  = excluded.sobrante_movido,
                ahorro_total_mes = excluded.ahorro_total_mes
        """, (user_id, mes, ahorro_extra, ocio_extra, ahorro_extra))
    st.cache_data.clear()

def fila_editable(item: dict, tipo: str, key_prefix: str):
    """Fila con botones ✏️ editar y 🗑️ borrar."""
    c1, c2, c3, c4, c5 = st.columns([4, 2, 2, 0.5, 0.5])
    c1.write(item.get("concepto", "—"))
    c2.write(item.get("categoria", item.get("prioridad", item.get("tipo", "—"))))
    c3.write(f"€{item['monto']:.2f}")

    ek = f"ed_{key_prefix}_{item['id']}"
    if c4.button("✏️", key=f"b{ek}", help="Editar"):
        st.session_state[ek] = True
    if c5.button("🗑️", key=f"d{ek}", help="Borrar"):
        if tipo == "ingreso":      borrar_ingreso(item["id"])
        elif tipo == "general":    borrar_gasto_general(item["id"])
        elif tipo == "importante": borrar_gasto_importante(item["id"])
        elif tipo == "casa":       borrar_gasto_casa(item["id"])
        st.rerun()

    if st.session_state.get(ek):
        with st.form(f"fmed_{key_prefix}_{item['id']}"):
            nc = st.text_input("Concepto", value=item.get("concepto", ""),
                               autocomplete="off")
            nm = st.number_input("Monto (€)", value=float(item["monto"]), min_value=0.01)
            cg, cc = st.columns(2)
            if cg.form_submit_button("Guardar"):
                tabla_map = {
                    "ingreso":    "ingresos",
                    "general":    "gastos_generales",
                    "importante": "gastos_importantes",
                    "casa":       "gastos_casa",
                }
                with get_db() as conn:
                    conn.execute(
                        f"UPDATE {tabla_map[tipo]} SET concepto=?, monto=? WHERE id=?",
                        (nc, nm, item["id"])
                    )
                st.cache_data.clear()
                st.session_state.pop(ek, None)
                st.rerun()
            if cc.form_submit_button("Cancelar"):
                st.session_state.pop(ek, None)
                st.rerun()


# ─────────────────────────────────────────
# CATEGORÍAS
# ─────────────────────────────────────────


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

def render_sidebar(sesion, hoy):
    st.markdown(f"### 👤 {sesion['nombre']}")
    st.caption(sesion["email"])
    st.divider()

    st.caption("Selecciona el mes activo")
    col_m, col_a = st.columns(2)
    mes_num = col_m.selectbox(
        "Mes", list(range(1, 13)),
        index=hoy.month - 1,
        format_func=lambda m: calendar.month_abbr[m],
    )
    anio_sel = col_a.number_input(
        "Año", min_value=2020, max_value=2035,
        value=hoy.year, step=1,
    )
    mes_sel = f"{int(anio_sel)}-{mes_num:02d}"

    cerrado = mes_cerrado(sesion["user_id"], mes_sel)
    if cerrado:
        st.warning(f"🔒 {mes_sel} cerrado")
    else:
        st.success(f"🟢 {mes_sel} activo")

    resumen_global = obtener_resumen_global(sesion["user_id"])
    st.divider()
    st.metric("🎯 Ahorro total", f"€{resumen_global['ahorro_total']:,.2f}")
    st.metric("🎉 Ocio total restante", f"€{resumen_global['ocio_total']:,.2f}")
    st.divider()
    pct_a = int(sesion["pct_ahorro"] * 100)
    st.caption(f"Ahorro: **{pct_a}%** · Ocio: **{100 - pct_a}%**")
    st.divider()
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        cerrar_sesion()

    return mes_sel, cerrado, anio_sel


@fragment
def render_ingreso_tab(sesion, hoy, d_prev):
    """Fragmento de ingreso aislado para no recargar todo el dashboard."""
    st.subheader("Registrar ingreso")

    if "reset_ingreso" not in st.session_state:
        st.session_state.reset_ingreso = False

   
    if st.session_state.reset_ingreso:
        st.session_state.m_ing = 0
        st.session_state.co_ing = ""
        st.session_state.reset_ingreso = False

    tipo_ing = st.radio("Tipo", ["Sueldo", "Extra"], horizontal=True)
    with st.form("frm_ing"):
        c1, c2 = st.columns(2)
        f_ing  = c1.date_input("Fecha", value=hoy, key="f_ing")
        m_ing  = c2.number_input("Monto (€)", min_value=0.01,
                                  value=None, placeholder="ej: 1200.00", step=50.0, key="m_ing")
        co_ing = st.text_input("Concepto", placeholder="Ej: Sueldo marzo",
                               autocomplete="off", key="co_ing")
        if st.form_submit_button("Guardar", use_container_width=True):
            if m_ing is None:
                st.error("Introduce un monto.")
            elif not co_ing:
                st.error("Escribe un concepto.")
            else:
                if tipo_ing == "Sueldo":
                    guardar_ingreso_sueldo(sesion["user_id"], str(f_ing), co_ing, m_ing)
                else:
                    guardar_ingreso_extra(sesion["user_id"], str(f_ing), co_ing, m_ing)
                st.success(f"Ingreso de €{m_ing:.2f} registrado.")
                st.session_state.reset_ingreso = True
                st.rerun()

    if d_prev["ing_total"] > 0:
        st.divider()
        st.caption("Vista previa de distribución:")
        c1, c2, c3 = st.columns(3)
        c1.metric("Remanente", f"€{d_prev['remanente']:.2f}")
        c2.metric(f"Ahorro ({int(d_prev['pct_ahorro']*100)}%)",
                   f"€{d_prev['ahorro_previsto']:.2f}")
        c3.metric(f"Ocio ({int(d_prev['pct_ocio']*100)}%)",
                   f"€{d_prev['ocio_previsto']:.2f}")


@fragment
def render_ocio_tab(sesion, hoy, mes_sel):
    """Fragmento de gasto de ocio aislado para mejorar la velocidad percibida."""
    st.subheader("Gasto de ocio")
    st.caption("Ropa, dulces, comida callejera, entretenimiento, salidas...")
    if "reset_ocio" not in st.session_state:
        st.session_state.reset_ocio = False
        
    if st.session_state.reset_ocio: 
        st.session_state.m_oc = 0
        st.session_state.co_oc = ""
        st.session_state.reset_ocio = False 
    
    with st.form("frm_ocio"):
        c1, c2 = st.columns(2)
        f_oc   = c1.date_input("Fecha", value=hoy)
        m_oc   = c2.number_input("Monto (€)", min_value=0.01,
                                  value=None, placeholder="ej: 25.00",
                                  step=5.0, key="m_oc")
        co_oc  = st.text_input("Concepto", placeholder="Ej: Camiseta",
                               autocomplete="off", key="co_oc")
        if st.form_submit_button("Guardar", use_container_width=True):
            if m_oc is None:
                st.error("Introduce un monto.")
            elif not co_oc:
                st.error("Escribe un concepto.")
            else:
                guardar_gasto_general(sesion["user_id"], str(f_oc), co_oc, m_oc, "Ocio")
                st.success("Gasto de ocio registrado.")
                st.session_state.reset_ocio = True
                st.rerun()


@fragment
def render_imprevisto_tab(sesion, hoy, mes_sel):
    """Fragmento de gasto imprevisto aislado para reducir efectos secundarios."""
    st.subheader("Gasto imprevisto importante")
    st.caption("Sale del remanente, reduciendo ahorro y ocio proporcionalmente.")

    if "reset_imprevisto" not in st.session_state:
        st.session_state.reset_imprevisto = False

    if st.session_state.reset_imprevisto: 
        st.session_state.m_im = 0
        st.session_state.co_im = ""
        st.session_state.reset_imprevisto = False 
    with st.form("frm_imp"):
        c1, c2 = st.columns(2)
        f_im   = c1.date_input("Fecha", value=hoy)
        m_im   = c2.number_input("Monto (€)", min_value=0.01,
                                  value=None, placeholder="ej: 50.00",
                                  step=10.0, key="m_im")
        co_im  = st.text_input("Concepto", placeholder="Ej: Médico urgente",
                               autocomplete="off", key="co_im")
        if st.form_submit_button("Guardar", use_container_width=True):
            if m_im is None:
                st.error("Introduce un monto.")
            elif not co_im:
                st.error("Escribe un concepto.")
            else:
                guardar_gasto_importante(sesion["user_id"], str(f_im), co_im, m_im, "media")
                red_a = round(m_im * sesion["pct_ahorro"], 2)
                red_o = round(m_im * sesion["pct_ocio"], 2)
                st.success(f"Registrado. Reduce ahorro €{red_a:.2f} · ocio €{red_o:.2f}")
                st.session_state.reset_imprevisto = True
                st.rerun()


@fragment
def render_casa_tab(sesion, hoy, mes_sel):
    """Fragmento de gasto fijo aislado para evitar recargar el resumen global."""
    st.subheader("Gastos fijos")
    st.caption("Arriendo, luz, agua, internet... Elige la categoría del previsto.")

    if "reset_casa" not in st.session_state:
        st.session_state.reset_casa = False

    if st.session_state.reset_casa: 
        st.session_state.m_ca = 0
        st.session_state.co_ca = ""
        st.session_state.reset_casa = False 

    fijos_cfg  = obtener_gastos_fijos(sesion["user_id"])
    estims_cfg = obtener_estimaciones(sesion["user_id"])
    cats_casa  = [f["concepto"] for f in fijos_cfg] + [e["concepto"] for e in estims_cfg]
    if not cats_casa:
        cats_casa = ["Otro"]
    else:
        cats_casa.append("Otro")

    with st.form("frm_cas"):
        c1, c2 = st.columns(2)
        f_ca   = c1.date_input("Fecha", value=hoy)
        m_ca   = c2.number_input("Monto (€)", min_value=0.01,
                                  value=None, placeholder="ej: 400.00",
                                  step=10.0, key="m_ca")
        co_ca  = st.text_input("Concepto", placeholder="Ej: Factura luz",
                               autocomplete="off", key="co_ca")
        cat_ca = st.selectbox("Categoría prevista", cats_casa)
        if st.form_submit_button("Guardar", use_container_width=True):
            if m_ca is None:
                st.error("Introduce un monto.")
            elif not co_ca:
                st.error("Escribe un concepto.")
            else:
                guardar_gasto_casa(
                    sesion["user_id"], str(f_ca), f"{cat_ca}: {co_ca}", m_ca, False
                )
                st.success(f"Gasto fijo registrado en '{cat_ca}'.")
                st.session_state.reset_casa = True
                st.rerun()


sesion = obtener_sesion()
hoy = date.today()
with st.sidebar:
    mes_sel, cerrado, anio_sel = render_sidebar(sesion, hoy)

dashboard = obtener_dashboard_contexto(sesion["user_id"], mes_sel, int(anio_sel))
d_mes = dashboard["mes"]


# ─────────────────────────────────────────
# PESTAÑAS
# ─────────────────────────────────────────

tab_res, tab_ing, tab_his, tab_cie, tab_cfg = st.tabs([
    "📊 Resumen", "➕ Ingresar", "📋 Historial", "🔒 Cierre", "⚙️ Config",
])


# ══════════════════════════════════════════
# PESTAÑA 1 — RESUMEN
# ══════════════════════════════════════════

with tab_res:
    st.header(f"Resumen — {mes_sel}")
    d = d_mes

    st.subheader("Estado del mes")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Ingresos",       f"€{d['ing_total']:,.2f}")
    c2.metric("📦 Gastos del Mes",   f"€{d['total_casa_gastado'] + d['total_ocio_gastado'] + d['total_imprevistos']:,.2f}")
    c3.metric("💾 Ahorro mensual",  f"€{d['ahorro_real']:,.2f}")
    c4.metric("🎉 Ocio disponible", f"€{d['ocio_disponible']:,.2f}")

    st.divider()

    st.subheader("💵 Ingresos")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total",  f"€{d['ing_total']:,.2f}")
    c2.metric("Sueldo", f"€{d['ing_sueldo']:,.2f}")
    c3.metric("Extras", f"€{d['ing_extras']:,.2f}")

    st.divider()

    st.subheader("📋 Plan del mes")
    st.caption("Previstos configurados vs lo que has gastado en gastos fijos este mes.")

    filas_plan = []
    for f in d["detalle_fijos"]:
        filas_plan.append({"Concepto": f["concepto"], "Tipo": "Fijo",
                           "Previsto": f["monto"]})
    for e in d["detalle_estim"]:
        filas_plan.append({"Concepto": e["concepto"], "Tipo": "Estimación",
                           "Previsto": e["promedio"]})
    for p in d["detalle_provis"]:
        filas_plan.append({"Concepto": p["concepto"], "Tipo": "Provisión /12",
                           "Previsto": p["cuota_mes"]})

    if filas_plan:
        gastado_por_cat = {}
        for gc in d["gastos_casa_lista"]:
            partes = gc["concepto"].split(":", 1)
            cat    = partes[0].strip() if len(partes) > 1 else "Otro"
            gastado_por_cat[cat] = gastado_por_cat.get(cat, 0) + gc["monto"]

        filas_comp = []
        for fila in filas_plan:
            cat        = fila["Concepto"]
            previsto   = fila["Previsto"]
            gastado    = gastado_por_cat.get(cat, 0)
            diferencia = round(previsto - gastado, 2)
            filas_comp.append({
                "Concepto":   cat,
                "Tipo":       fila["Tipo"],
                "Previsto":   f"€{previsto:.2f}",
                "Gastado":    f"€{gastado:.2f}" if gastado > 0 else "—",
                "Diferencia": f"€{diferencia:.2f}",
                "Estado":     "✅ Dentro" if diferencia >= 0 else "⚠️ Excedido",
            })

        st.dataframe(filas_comp, hide_index=True, use_container_width=True)

        total_gastado_casa = sum(gastado_por_cat.values())
        diferencia_plan    = round(d["total_previstos"] - total_gastado_casa, 2)
        c1, c2 = st.columns(2)
        c1.metric("Total previstos",     f"€{d['total_previstos']:,.2f}")
        c2.metric("Total gastado",  f"€{total_gastado_casa:,.2f}",
                  delta=f"€{diferencia_plan:.2f} restante" if diferencia_plan >= 0
                        else f"€{abs(diferencia_plan):.2f} excedido",
                  delta_color="normal" if diferencia_plan >= 0 else "inverse")
    else:
        st.info("No tienes gastos configurados. Ve a ⚙️ Config para agregar fijos, estimaciones o provisiones.")

    st.divider()

    st.subheader("📅 Histórico del año")
    hist = dashboard["hist"]
    if hist:
        st.dataframe(
            hist, hide_index=True, use_container_width=True,
            column_config={
                "mes":         "Mes",
                "ingresos":    st.column_config.NumberColumn("Ingresos €",    format="€%.2f"),
                "previstos":   st.column_config.NumberColumn("Gastos del mes €",   format="€%.2f"),
                "imprevistos": st.column_config.NumberColumn("Imprevistos €", format="€%.2f"),
                "ocio_gast":   st.column_config.NumberColumn("Ocio gastado €",format="€%.2f"),
                "ahorro":      st.column_config.NumberColumn("Ahorro €",      format="€%.2f"),
            }
        )
    else:
        st.info("Sin datos este año.")


# ══════════════════════════════════════════
# PESTAÑA 2 — INGRESAR
# ══════════════════════════════════════════

with tab_ing:
    st.header("Ingresar datos")

    if cerrado:
        st.error(f"🔒 El mes {mes_sel} está cerrado. Ve a 'Cierre' para desbloquearlo.")
    else:
        sub1, sub2, sub3, sub4 = st.tabs([
            "💼 Ingresos", "🛒 Ocio", "⚠️ Imprevisto", "🏠 Gastos fijos"
        ])

        # ── Ingresos ─────────────────────
        with sub1:
            render_ingreso_tab(sesion, hoy, d_mes)

        # ── Ocio ─────────────────────────
        with sub2:
            render_ocio_tab(sesion, hoy, mes_sel)

        # ── Imprevisto ────────────────────
        with sub3:
            render_imprevisto_tab(sesion, hoy, mes_sel)

        # ── Gastos fijos ─────────────────────────
        with sub4:
            render_casa_tab(sesion, hoy, mes_sel)


# ══════════════════════════════════════════
# PESTAÑA 3 — HISTORIAL
# ══════════════════════════════════════════

with tab_his:
    st.header(f"Historial — {mes_sel}")

    sh1, sh2, sh3, sh4 = st.tabs([
        "Ingresos", "Ocio", "Imprevistos + Gastos fijos", "Todos los movimientos"
    ])

    with sh1:
        items = dashboard["ingresos"]
        if items:
            for it in items:
                fila_editable({**it, "categoria": it.get("tipo", "")}, "ingreso", "ing")
            total = dashboard["totales_historial"]["ingresos"]
            st.markdown(f"**Total: €{total:.2f}**")
        else:
            st.info("Sin ingresos este mes.")

    with sh2:
        items = dashboard["gastos_ocio"]
        if items:
            for it in items:
                fila_editable(it, "general", "oc")
            total = dashboard["totales_historial"]["ocio"]
            st.markdown(f"**Total ocio: €{total:.2f}**")
        else:
            st.info("Sin gastos de ocio este mes.")

    with sh3:
        imp = d["gastos_imp_lista"]
        cas = d["gastos_casa_lista"]
        if imp:
            st.caption("⚠️ Imprevistos importantes")
            for it in imp:
                fila_editable(it, "importante", "im")
            st.markdown(f"**Total imprevistos: €{dashboard['totales_historial']['imprevistos']:.2f}**")
        if cas:
            st.caption("🏠 Gastos fijos")
            for it in cas:
                fila_editable(
                    {**it, "categoria": it["concepto"].split(":")[0]
                     if ":" in it["concepto"] else "—"},
                    "casa", "ca"
                )
            st.markdown(f"**Total gastos fijos: €{dashboard['totales_historial']['casa']:.2f}**")
        if not imp and not cas:
            st.info("Sin imprevistos ni gastos fijos este mes.")

    with sh4:
        todos = dashboard["todos"]
        if todos:
            st.dataframe(
                todos,
                hide_index=True, use_container_width=True,
                column_config={
                    "fecha":    st.column_config.DateColumn("Fecha"),
                    "tipo":     "Tipo",
                    "concepto": "Concepto",
                    "monto":    st.column_config.NumberColumn("Monto €", format="€%.2f"),
                }
            )
        else:
            st.info("Sin movimientos este mes.")


# ══════════════════════════════════════════
# PESTAÑA 4 — CIERRE DE MES
# ══════════════════════════════════════════

with tab_cie:
    st.header(f"Cierre de mes — {mes_sel}")

    if cerrado:
        st.success(f"✅ El mes {mes_sel} está cerrado.")
        d_ro = d_mes
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos",       f"€{d_ro['ing_total']:.2f}")
        c2.metric("Ahorro mensual", f"€{d_ro['ahorro_real']:.2f}")
        c3.metric("Ocio gastado",   f"€{d_ro['total_ocio_gastado']:.2f}")
        st.divider()
        st.caption("Desbloquear elimina el cierre — podrás volver a editar datos.")
        if st.button("🔓 Desbloquear mes para editar", type="secondary"):
            desbloquear_mes(sesion["user_id"], mes_sel)
            st.success("Mes desbloqueado.")
            st.rerun()
    else:
        d_cie = d_mes

        st.subheader("Resumen antes de cerrar")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingresos",    f"€{d_cie['ing_total']:.2f}")
        c2.metric("Gastos fijos €",   f"€{d_cie['total_previstos']:.2f}")
        c3.metric("Imprevistos", f"€{d_cie['total_imprevistos']:.2f}")
        c4.metric("Ocio gastado",f"€{d_cie['total_ocio_gastado']:.2f}")

        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("💾 Ahorro mensual",       f"€{d_cie['ahorro_real']:.2f}")
        c2.metric("🎉 Ocio disponible rest.", f"€{d_cie['ocio_disponible']:.2f}")

        st.divider()
        st.subheader("Sobrante de gastos previstos")
        sobrante = d_cie["sobrante_previstos"]

        if sobrante > 0:
            st.info(f"Te sobran **€{sobrante:.2f}** de los gastos previstos.")
            dest = st.radio(
                "¿Dónde mover el sobrante?",
                ["Sumar al ahorro", "Sumar al ocio", "Dividir (50/50)"],
                horizontal=True,
            )
            if dest == "Sumar al ahorro":
                ahorro_extra, ocio_extra = sobrante, 0.0
            elif dest == "Sumar al ocio":
                ahorro_extra, ocio_extra = 0.0, sobrante
            else:
                ahorro_extra = ocio_extra = round(sobrante / 2, 2)
            st.caption(
                f"Ahorro final: €{d_cie['ahorro_real'] + ahorro_extra:.2f} · "
                f"Ocio final: €{d_cie['ocio_disponible'] + ocio_extra:.2f}"
            )
        else:
            ahorro_extra = ocio_extra = 0.0
            st.caption("Sin sobrante de previstos este mes.")

        st.divider()
        if st.button("✅ Confirmar y cerrar el mes", type="primary", use_container_width=True):
            guardar_cierre(sesion["user_id"], mes_sel, ahorro_extra, ocio_extra)
            st.success(f"✅ Mes cerrado. Ahorro: **€{d_cie['ahorro_real'] + ahorro_extra:.2f}**")
            st.balloons()
            st.rerun()


# ══════════════════════════════════════════
# PESTAÑA 5 — CONFIGURACIÓN
# ══════════════════════════════════════════

with tab_cfg:
    st.header("Configuración")

    cfg1, cfg2, cfg3, cfg4 = st.tabs([
        "💰 % Ahorro", "🏠 Gastos fijos", "🛒 Estimaciones", "📅 Provisiones"
    ])

    with cfg1:
        st.subheader("Distribución del remanente")
        st.caption("Se aplica sobre lo que sobra después de restar los gastos previstos.")
        pct_actual = int(sesion["pct_ahorro"] * 100)
        nuevo_pct  = st.slider("% de ahorro", 10, 90, pct_actual, step=5, format="%d%%")
        c1, c2     = st.columns(2)
        c1.metric("Ahorro", f"{nuevo_pct}%")
        c2.metric("Ocio",   f"{100 - nuevo_pct}%")
        if st.button("Guardar", use_container_width=True):
            if actualizar_pct_ahorro(sesion["user_id"], nuevo_pct / 100):
                st.session_state["pct_ahorro"] = nuevo_pct / 100
                st.session_state["pct_ocio"]   = round(1 - nuevo_pct / 100, 2)
                st.success("Porcentaje actualizado.")
                st.rerun()

    with cfg2:
        st.subheader("Gastos fijos mensuales")
        st.caption("Arriendo, servicios... se restan cada mes antes de calcular el ahorro.")
        for f in obtener_gastos_fijos(sesion["user_id"]):
            c1, c2, c3 = st.columns([5, 2, 1])
            c1.write(f["concepto"])
            c2.write(f"€{f['monto']:.2f}/mes")
            if c3.button("🗑️", key=f"df_{f['id']}"):
                desactivar_gasto_fijo(sesion["user_id"], f["id"])
                st.rerun()
        with st.form("frm_fijo"):
            c1, c2 = st.columns(2)
            cn_f   = c1.text_input("Concepto", placeholder="Arriendo",
                                    autocomplete="off")
            mo_f   = c2.number_input("Monto (€)", min_value=0.01,
                                      value=None, placeholder="ej: 600.00", step=10.0)
            if st.form_submit_button("Agregar", use_container_width=True):
                if mo_f is None:
                    st.error("Introduce un monto.")
                elif cn_f:
                    guardar_gasto_fijo(sesion["user_id"], cn_f, mo_f)
                    st.rerun()

    with cfg3:
        st.subheader("Estimaciones mensuales")
        st.caption("Comida, gasolina... promedios variables que reservas cada mes.")
        for e in obtener_estimaciones(sesion["user_id"]):
            c1, c2, c3 = st.columns([5, 2, 1])
            c1.write(e["concepto"])
            c2.write(f"€{e['promedio']:.2f}/mes")
            if c3.button("🗑️", key=f"de_{e['id']}"):
                desactivar_estimacion(sesion["user_id"], e["id"])
                st.rerun()
        with st.form("frm_estim"):
            c1, c2 = st.columns(2)
            cn_e   = c1.text_input("Concepto", placeholder="Comida",
                                    autocomplete="off")
            mo_e   = c2.number_input("Promedio (€)", min_value=0.01,
                                      value=None, placeholder="ej: 200.00", step=10.0)
            if st.form_submit_button("Agregar", use_container_width=True):
                if mo_e is None:
                    st.error("Introduce un monto.")
                elif cn_e:
                    guardar_estimacion(sesion["user_id"], cn_e, mo_e)
                    st.rerun()

    with cfg4:
        st.subheader("Provisiones anuales")
        st.caption("Seguro, ITV... se divide entre 12 y se reserva cada mes.")
        for p in obtener_provisiones(sesion["user_id"]):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(p["concepto"])
            c2.write(f"€{p['monto_anual']:.2f}/año")
            c3.write(f"€{p['cuota_mes']:.2f}/mes")
            if c4.button("🗑️", key=f"dp_{p['id']}"):
                desactivar_provision(sesion["user_id"], p["id"])
                st.rerun()
        with st.form("frm_prov"):
            c1, c2 = st.columns(2)
            cn_p   = c1.text_input("Concepto", placeholder="Seguro carro",
                                    autocomplete="off")
            mo_an  = c2.number_input("Monto anual (€)", min_value=0.01,
                                      value=None, placeholder="ej: 600.00", step=50.0)
            if mo_an:
                st.caption(f"Reserva mensual: **€{mo_an / 12:.2f}**")
            if st.form_submit_button("Agregar", use_container_width=True):
                if mo_an is None:
                    st.error("Introduce un monto.")
                elif cn_p:
                    guardar_provision(sesion["user_id"], cn_p, mo_an)
                    st.rerun()
