#NOTA: Cambie el nombre de Gastos casa a Gastos fijos, ya que es más representativo de lo que realmente son, y permite incluir otros gastos previstos que no sean solo de casa. las variables no las toque tomar en cuenta.

"""
app.py — App de Finanzas Personales
Ejecutar: streamlit run app.py
"""

import streamlit as st
import database as db
from datetime import date
from i18n import (
    t,
    month_abbr,
    get_language,
    set_language,
    clear_language_override,
    language_options,
    language_label,
)

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
from charts import render_torta
from logic import (
    obtener_dashboard_contexto, obtener_resumen_global,
)

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────

st.set_page_config(
    page_title=t("Mis Finanzas"),
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
    if c4.button("✏️", key=f"b{ek}", help=t("Editar")):
        st.session_state[ek] = True
    if c5.button("🗑️", key=f"d{ek}", help=t("Borrar")):
        if tipo == "ingreso":      borrar_ingreso(item["id"])
        elif tipo == "general":    borrar_gasto_general(item["id"])
        elif tipo == "importante": borrar_gasto_importante(item["id"])
        elif tipo == "casa":       borrar_gasto_casa(item["id"])
        st.rerun()

    if st.session_state.get(ek):
        with st.form(f"fmed_{key_prefix}_{item['id']}"):
            nc = st.text_input(t("Concepto"), value=item.get("concepto", ""),
                               autocomplete="off")
            nm = st.number_input(t("Monto (€)"), value=float(item["monto"]), min_value=0.01)
            cg, cc = st.columns(2)
            if cg.form_submit_button(t("Guardar")):
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
            if cc.form_submit_button(t("Cancelar")):
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

    current_lang = get_language()
    selected_lang = st.selectbox(
        "Language",
        language_options(),
        index=language_options().index(current_lang),
        format_func=language_label,
        key="ui_language_select",
    )
    c_lang_1, c_lang_2 = st.columns(2)
    if c_lang_1.button("Apply", width="stretch"):
        if selected_lang != current_lang or st.session_state.get("lang_source") != "manual":
            set_language(selected_lang)
            st.rerun()
    if c_lang_2.button("Auto", width="stretch"):
        clear_language_override()
        st.rerun()

    st.caption(f"Detected browser language: `{getattr(st.context, 'locale', 'unknown') or 'unknown'}`")
    st.divider()

    st.caption(t("Selecciona el mes activo"))
    col_m, col_a = st.columns(2)
    mes_num = col_m.selectbox(
        t("Mes"), list(range(1, 13)),
        index=hoy.month - 1,
        format_func=month_abbr,
    )
    anio_sel = col_a.number_input(
        t("Año"), min_value=2020, max_value=2035,
        value=hoy.year, step=1,
    )
    mes_sel = f"{int(anio_sel)}-{mes_num:02d}"

    cerrado = mes_cerrado(sesion["user_id"], mes_sel)
    if cerrado:
        st.warning(t("🔒 {month} cerrado", month=mes_sel))
    else:
        st.success(t("🟢 {month} activo", month=mes_sel))

    resumen_global = obtener_resumen_global(sesion["user_id"])
    st.divider()
    st.metric(t("🎯 Ahorro total"), f"€{resumen_global['ahorro_total']:,.2f}")
    st.metric(t("🎉 Ocio total restante"), f"€{resumen_global['ocio_total']:,.2f}")
    st.divider()
    pct_a = int(sesion["pct_ahorro"] * 100)
    st.caption(t("Ahorro: **{save}%** · Ocio: **{fun}%**", save=pct_a, fun=100 - pct_a))
    st.divider()
    if st.button(t("🚪 Cerrar sesión"), width="stretch"):
        cerrar_sesion()

    return mes_sel, cerrado, anio_sel


@fragment
def render_ingreso_tab(sesion, hoy, d_prev):
    """Fragmento de ingreso aislado para no recargar todo el dashboard."""
    st.subheader(t("Registrar ingreso"))

    if "reset_ingreso" not in st.session_state:
        st.session_state.reset_ingreso = False

   
    if st.session_state.reset_ingreso:
        st.session_state.m_ing = 0
        st.session_state.co_ing = ""
        st.session_state.reset_ingreso = False

    tipo_ing = st.radio(t("Tipo"), [t("Sueldo"), t("Extra")], horizontal=True)
    with st.form("frm_ing"):
        c1, c2 = st.columns(2)
        f_ing  = c1.date_input(t("Fecha"), value=hoy, key="f_ing")
        m_ing  = c2.number_input(t("Monto (€)"), min_value=0.01,
                                  value=None, placeholder="ej: 1200.00", step=50.0, key="m_ing")
        co_ing = st.text_input(t("Concepto"), placeholder="Ej: Sueldo marzo",
                               autocomplete="off", key="co_ing")
        if st.form_submit_button(t("Guardar"), width="stretch"):
            if m_ing is None:
                st.error(t("Introduce un monto."))
            elif not co_ing:
                st.error(t("Escribe un concepto."))
            else:
                if tipo_ing == t("Sueldo"):
                    guardar_ingreso_sueldo(sesion["user_id"], str(f_ing), co_ing, m_ing)
                else:
                    guardar_ingreso_extra(sesion["user_id"], str(f_ing), co_ing, m_ing)
                st.success(t("Ingreso de €{amount:.2f} registrado.", amount=m_ing))
                st.session_state.reset_ingreso = True
                st.rerun()

    if d_prev["ing_total"] > 0:
        st.divider()
        st.caption(t("Vista previa de distribución:"))
        c1, c2, c3 = st.columns(3)
        c1.metric(t("Remanente"), f"€{d_prev['remanente']:.2f}")
        c2.metric(f"{t('Ahorro')} ({int(d_prev['pct_ahorro']*100)}%)",
                   f"€{d_prev['ahorro_previsto']:.2f}")
        c3.metric(f"{t('Ocio')} ({int(d_prev['pct_ocio']*100)}%)",
                   f"€{d_prev['ocio_previsto']:.2f}")


@fragment
def render_ocio_tab(sesion, hoy, mes_sel):
    """Fragmento de gasto de ocio aislado para mejorar la velocidad percibida."""
    st.subheader(t("Gasto de ocio"))
    st.caption(t("Ropa, dulces, comida callejera, entretenimiento, salidas..."))
    if "reset_ocio" not in st.session_state:
        st.session_state.reset_ocio = False
        
    if st.session_state.reset_ocio: 
        st.session_state.m_oc = 0
        st.session_state.co_oc = ""
        st.session_state.reset_ocio = False 
    
    with st.form("frm_ocio"):
        c1, c2 = st.columns(2)
        f_oc   = c1.date_input(t("Fecha"), value=hoy)
        m_oc   = c2.number_input(t("Monto (€)"), min_value=0.01,
                                  value=None, placeholder="ej: 25.00",
                                  step=5.0, key="m_oc")
        co_oc  = st.text_input(t("Concepto"), placeholder="Ej: Camiseta",
                               autocomplete="off", key="co_oc")
        if st.form_submit_button(t("Guardar"), width="stretch"):
            if m_oc is None:
                st.error(t("Introduce un monto."))
            elif not co_oc:
                st.error(t("Escribe un concepto."))
            else:
                guardar_gasto_general(sesion["user_id"], str(f_oc), co_oc, m_oc, "Ocio")
                st.success(t("Gasto de ocio registrado."))
                st.session_state.reset_ocio = True
                st.rerun()


@fragment
def render_imprevisto_tab(sesion, hoy, mes_sel):
    """Fragmento de gasto imprevisto aislado para reducir efectos secundarios."""
    st.subheader(t("Gasto imprevisto importante"))
    st.caption(t("Sale del remanente, reduciendo ahorro y ocio proporcionalmente."))

    if "reset_imprevisto" not in st.session_state:
        st.session_state.reset_imprevisto = False

    if st.session_state.reset_imprevisto: 
        st.session_state.m_im = 0
        st.session_state.co_im = ""
        st.session_state.reset_imprevisto = False 
    with st.form("frm_imp"):
        c1, c2 = st.columns(2)
        f_im   = c1.date_input(t("Fecha"), value=hoy)
        m_im   = c2.number_input(t("Monto (€)"), min_value=0.01,
                                  value=None, placeholder="ej: 50.00",
                                  step=10.0, key="m_im")
        co_im  = st.text_input(t("Concepto"), placeholder="Ej: Médico urgente",
                               autocomplete="off", key="co_im")
        if st.form_submit_button(t("Guardar"), width="stretch"):
            if m_im is None:
                st.error(t("Introduce un monto."))
            elif not co_im:
                st.error(t("Escribe un concepto."))
            else:
                guardar_gasto_importante(sesion["user_id"], str(f_im), co_im, m_im, "media")
                red_a = round(m_im * sesion["pct_ahorro"], 2)
                red_o = round(m_im * sesion["pct_ocio"], 2)
                st.success(t("Registrado. Reduce ahorro €{save:.2f} · ocio €{fun:.2f}", save=red_a, fun=red_o))
                st.session_state.reset_imprevisto = True
                st.rerun()


@fragment
def render_casa_tab(sesion, hoy, mes_sel):
    """Fragmento de gasto fijo aislado para evitar recargar el resumen global."""
    st.subheader(t("Gastos fijos"))
    st.caption(t("Arriendo, luz, agua, internet... Elige la categoría del previsto."))

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
        cats_casa = [t("Otro")]
    else:
        cats_casa.append(t("Otro"))

    with st.form("frm_cas"):
        c1, c2 = st.columns(2)
        f_ca   = c1.date_input(t("Fecha"), value=hoy)
        m_ca   = c2.number_input(t("Monto (€)"), min_value=0.01,
                                  value=None, placeholder="ej: 400.00",
                                  step=10.0, key="m_ca")
        co_ca  = st.text_input(t("Concepto"), placeholder="Ej: Factura luz",
                               autocomplete="off", key="co_ca")
        cat_ca = st.selectbox(t("Categoría prevista"), cats_casa)
        if st.form_submit_button(t("Guardar"), width="stretch"):
            if m_ca is None:
                st.error(t("Introduce un monto."))
            elif not co_ca:
                st.error(t("Escribe un concepto."))
            else:
                guardar_gasto_casa(
                    sesion["user_id"], str(f_ca), f"{cat_ca}: {co_ca}", m_ca, False
                )
                st.success(t("Gasto fijo registrado en '{category}'.", category=cat_ca))
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
    t("📊 Resumen"), t("➕ Ingresar"), t("📋 Historial"), t("🔒 Cierre"), t("⚙️ Config"),
])


# ══════════════════════════════════════════
# PESTAÑA 1 — RESUMEN
# ══════════════════════════════════════════

with tab_res:
    st.header(t("Resumen — {month}", month=mes_sel))
    d = d_mes

    total_gastos_mes = d["total_casa_gastado"] + d["total_ocio_gastado"] + d["total_imprevistos"]
    col_izq, col_der = st.columns([1.0, 1.4], gap="large")
    with col_izq:
        st.subheader("Estado del mes")
    c1 = col_izq
    c2 = col_izq
    c3 = col_izq
    c4 = col_izq

    with col_der:
        g1, g2 = st.columns(2, gap="medium")
        with g1:
            render_torta(
                "DistribuciÃ³n de gastos del mes",
                [t("Gastos fijos"), t("Ocio"), t("Imprevistos")],
                [d["total_casa_gastado"], d["total_ocio_gastado"], d["total_imprevistos"]],
            )
        with g2:
            render_torta(
                "DistribuciÃ³n de ingresos del mes",
                [t("Sueldo"), t("Extras")],
                [d["ing_sueldo"], d["ing_extras"]],
            )
    c1.metric(t("💵 Ingresos"), f"€{d['ing_total']:,.2f}")
    c2.metric(t("📦 Gastos del Mes"), f"€{d['total_casa_gastado'] + d['total_ocio_gastado'] + d['total_imprevistos']:,.2f}")
    c3.metric(t("💾 Ahorro mensual"), f"€{d['ahorro_real']:,.2f}")
    c4.metric(t("🎉 Ocio disponible"), f"€{d['ocio_disponible']:,.2f}")

    st.divider()

    # st.subheader(t("💵 Ingresos"))
    # c1, c2, c3 = st.columns(3)
    # c1.metric(t("Total"),  f"€{d['ing_total']:,.2f}")
    # c2.metric(t("Sueldo"), f"€{d['ing_sueldo']:,.2f}")
    # c3.metric(t("Extras"), f"€{d['ing_extras']:,.2f}")

    #st.divider()

    st.subheader(t("📋 Plan del mes"))
    st.caption(t("Previstos configurados vs lo que has gastado en gastos fijos este mes."))

    filas_plan = []
    for f in d["detalle_fijos"]:
        filas_plan.append({"Concepto": f["concepto"], "Tipo": t("Fijo"),
                           "Previsto": f["monto"]})
    for e in d["detalle_estim"]:
        filas_plan.append({"Concepto": e["concepto"], "Tipo": t("Estimación"),
                           "Previsto": e["promedio"]})
    for p in d["detalle_provis"]:
        filas_plan.append({"Concepto": p["concepto"], "Tipo": t("Provisión /12"),
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
                "Estado":     t("✅ Dentro") if diferencia >= 0 else t("⚠️ Excedido"),
            })

        st.dataframe(filas_comp, hide_index=True, width="stretch")

        total_gastado_casa = sum(gastado_por_cat.values())
        diferencia_plan    = round(d["total_previstos"] - total_gastado_casa, 2)
        c1, c2 = st.columns(2)
        c1.metric(t("Total previstos"), f"€{d['total_previstos']:,.2f}")
        c2.metric(t("Total gastado"), f"€{total_gastado_casa:,.2f}",
                  delta=t("€{amount:.2f} restante", amount=diferencia_plan) if diferencia_plan >= 0
                        else t("€{amount:.2f} excedido", amount=abs(diferencia_plan)),
                  delta_color="normal" if diferencia_plan >= 0 else "inverse")
    else:
        st.info(t("No tienes gastos configurados. Ve a ⚙️ Config para agregar fijos, estimaciones o provisiones."))

    st.divider()

    st.subheader(t("📅 Histórico del año"))
    hist = dashboard["hist"]
    if hist:
        st.dataframe(
            hist, hide_index=True, width="stretch",
            column_config={
                "mes": "Mes" if get_language() == "es" else "Month",
                "ingresos": st.column_config.NumberColumn(f"{t('Ingresos')} €", format="€%.2f"),
                "previstos": st.column_config.NumberColumn(("Gastos del mes" if get_language() == "es" else "Monthly expenses") + " €", format="€%.2f"),
                "imprevistos": st.column_config.NumberColumn(("Imprevistos" if get_language() == "es" else "Unexpected") + " €", format="€%.2f"),
                "ocio_gast": st.column_config.NumberColumn(f"{t('Ocio gastado')} €", format="€%.2f"),
                "ahorro": st.column_config.NumberColumn(f"{t('Ahorro')} €", format="€%.2f"),
            }
        )
    else:
        st.info(t("Sin datos este año."))


# ══════════════════════════════════════════
# PESTAÑA 2 — INGRESAR
# ══════════════════════════════════════════

with tab_ing:
    st.header(t("Ingresar datos"))

    if cerrado:
        st.error(t("🔒 El mes {month} está cerrado. Ve a 'Cierre' para desbloquearlo.", month=mes_sel))
    else:
        sub1, sub2, sub3, sub4 = st.tabs([
            t("💼 Ingresos"), t("🛒 Ocio"), t("⚠️ Imprevisto"), t("🏠 Gastos fijos")
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
    st.header(t("Historial — {month}", month=mes_sel))

    sh1, sh2, sh3, sh4 = st.tabs([
        t("Ingresos"), t("Ocio"), t("Imprevistos + Gastos fijos"), t("Todos los movimientos")
    ])

    with sh1:
        items = dashboard["ingresos"]
        if items:
            for it in items:
                fila_editable({**it, "categoria": it.get("tipo", "")}, "ingreso", "ing")
            total = dashboard["totales_historial"]["ingresos"]
            st.markdown(f"**{t('Total: €{amount:.2f}', amount=total)}**")
        else:
            st.info(t("Sin ingresos este mes."))

    with sh2:
        items = dashboard["gastos_ocio"]
        if items:
            for it in items:
                fila_editable(it, "general", "oc")
            total = dashboard["totales_historial"]["ocio"]
            st.markdown(f"**{t('Total ocio: €{amount:.2f}', amount=total)}**")
        else:
            st.info(t("Sin gastos de ocio este mes."))

    with sh3:
        imp = d["gastos_imp_lista"]
        cas = d["gastos_casa_lista"]
        if imp:
            st.caption(t("⚠️ Imprevistos importantes"))
            for it in imp:
                fila_editable(it, "importante", "im")
            st.markdown(f"**{t('Total imprevistos: €{amount:.2f}', amount=dashboard['totales_historial']['imprevistos'])}**")
        if cas:
            st.caption(t("🏠 Gastos fijos"))
            for it in cas:
                fila_editable(
                    {**it, "categoria": it["concepto"].split(":")[0]
                     if ":" in it["concepto"] else "—"},
                    "casa", "ca"
                )
            st.markdown(f"**{t('Total gastos fijos: €{amount:.2f}', amount=dashboard['totales_historial']['casa'])}**")
        if not imp and not cas:
            st.info(t("Sin imprevistos ni gastos fijos este mes."))

    with sh4:
        todos = dashboard["todos"]
        if todos:
            st.dataframe(
                todos,
                hide_index=True, width="stretch",
                column_config={
                    "fecha": st.column_config.DateColumn(t("Fecha")),
                    "tipo": t("Tipo"),
                    "concepto": t("Concepto"),
                    "monto": st.column_config.NumberColumn(f"{t('Monto (€)').replace('(€)', '€')}", format="€%.2f"),
                }
            )
        else:
            st.info(t("Sin movimientos este mes."))


# ══════════════════════════════════════════
# PESTAÑA 4 — CIERRE DE MES
# ══════════════════════════════════════════

with tab_cie:
    st.header(t("Cierre de mes — {month}", month=mes_sel))

    if cerrado:
        st.success(t("✅ El mes {month} está cerrado.", month=mes_sel))
        d_ro = d_mes
        c1, c2, c3 = st.columns(3)
        c1.metric(t("Ingresos"), f"€{d_ro['ing_total']:.2f}")
        c2.metric(t("💾 Ahorro mensual"), f"€{d_ro['ahorro_real']:.2f}")
        c3.metric(t("Ocio gastado"), f"€{d_ro['total_ocio_gastado']:.2f}")
        st.divider()
        st.caption(t("Desbloquear elimina el cierre — podrás volver a editar datos."))
        if st.button(t("🔓 Desbloquear mes para editar"), type="secondary"):
            desbloquear_mes(sesion["user_id"], mes_sel)
            st.success(t("Mes desbloqueado."))
            st.rerun()
    else:
        d_cie = d_mes

        st.subheader(t("Resumen antes de cerrar"))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("Ingresos"), f"€{d_cie['ing_total']:.2f}")
        c2.metric(t("Gastos fijos €"), f"€{d_cie['total_previstos']:.2f}")
        c3.metric("Imprevistos" if get_language() == "es" else "Unexpected", f"€{d_cie['total_imprevistos']:.2f}")
        c4.metric(t("Ocio gastado"), f"€{d_cie['total_ocio_gastado']:.2f}")

        st.divider()
        c1, c2 = st.columns(2)
        c1.metric(t("💾 Ahorro mensual"), f"€{d_cie['ahorro_real']:.2f}")
        c2.metric(t("🎉 Ocio disponible rest."), f"€{d_cie['ocio_disponible']:.2f}")

        st.divider()
        st.subheader(t("Sobrante de gastos previstos"))
        sobrante = d_cie["sobrante_previstos"]

        if sobrante > 0:
            st.info(t("Te sobran **€{amount:.2f}** de los gastos previstos.", amount=sobrante))
            dest = st.radio(
                t("¿Dónde mover el sobrante?"),
                [t("Sumar al ahorro"), t("Sumar al ocio"), t("Dividir (50/50)")],
                horizontal=True,
            )
            if dest == t("Sumar al ahorro"):
                ahorro_extra, ocio_extra = sobrante, 0.0
            elif dest == t("Sumar al ocio"):
                ahorro_extra, ocio_extra = 0.0, sobrante
            else:
                ahorro_extra = ocio_extra = round(sobrante / 2, 2)
            st.caption(t(
                "Ahorro final: €{save:.2f} · Ocio final: €{fun:.2f}",
                save=d_cie["ahorro_real"] + ahorro_extra,
                fun=d_cie["ocio_disponible"] + ocio_extra,
            ))
        else:
            ahorro_extra = ocio_extra = 0.0
            st.caption(t("Sin sobrante de previstos este mes."))

        st.divider()
        if st.button(t("✅ Confirmar y cerrar el mes"), type="primary", width="stretch"):
            guardar_cierre(sesion["user_id"], mes_sel, ahorro_extra, ocio_extra)
            st.success(t("✅ Mes cerrado. Ahorro: **€{amount:.2f}**", amount=d_cie["ahorro_real"] + ahorro_extra))
            st.balloons()
            st.rerun()


# ══════════════════════════════════════════
# PESTAÑA 5 — CONFIGURACIÓN
# ══════════════════════════════════════════

with tab_cfg:
    st.header(t("Configuración"))

    cfg1, cfg2, cfg3, cfg4 = st.tabs([
        t("💰 % Ahorro"), t("🏠 Gastos fijos"), t("🛒 Estimaciones"), t("📅 Provisiones")
    ])

    with cfg1:
        st.subheader(t("Distribución del remanente"))
        st.caption(t("Se aplica sobre lo que sobra después de restar los gastos previstos."))
        pct_actual = int(sesion["pct_ahorro"] * 100)
        nuevo_pct  = st.slider(t("% de ahorro"), 10, 90, pct_actual, step=5, format="%d%%")
        c1, c2     = st.columns(2)
        c1.metric(t("Ahorro"), f"{nuevo_pct}%")
        c2.metric(t("Ocio"),   f"{100 - nuevo_pct}%")
        if st.button(t("Guardar"), width="stretch"):
            if actualizar_pct_ahorro(sesion["user_id"], nuevo_pct / 100):
                st.session_state["pct_ahorro"] = nuevo_pct / 100
                st.session_state["pct_ocio"]   = round(1 - nuevo_pct / 100, 2)
                st.success(t("Porcentaje actualizado."))
                st.rerun()

    with cfg2:
        st.subheader(t("Gastos fijos mensuales"))
        st.caption(t("Arriendo, servicios... se restan cada mes antes de calcular el ahorro."))
        for f in obtener_gastos_fijos(sesion["user_id"]):
            c1, c2, c3 = st.columns([5, 2, 1])
            c1.write(f["concepto"])
            c2.write(f"€{f['monto']:.2f}/mes")
            if c3.button("🗑️", key=f"df_{f['id']}", help=t("Borrar")):
                desactivar_gasto_fijo(sesion["user_id"], f["id"])
                st.rerun()
        with st.form("frm_fijo"):
            c1, c2 = st.columns(2)
            cn_f   = c1.text_input(t("Concepto"), placeholder="Arriendo",
                                    autocomplete="off")
            mo_f   = c2.number_input(t("Monto (€)"), min_value=0.01,
                                      value=None, placeholder="ej: 600.00", step=10.0)
            if st.form_submit_button(t("Agregar"), width="stretch"):
                if mo_f is None:
                    st.error(t("Introduce un monto."))
                elif cn_f:
                    guardar_gasto_fijo(sesion["user_id"], cn_f, mo_f)
                    st.rerun()

    with cfg3:
        st.subheader(t("Estimaciones mensuales"))
        st.caption(t("Comida, gasolina... promedios variables que reservas cada mes."))
        for e in obtener_estimaciones(sesion["user_id"]):
            c1, c2, c3 = st.columns([5, 2, 1])
            c1.write(e["concepto"])
            c2.write(f"€{e['promedio']:.2f}/mes")
            if c3.button("🗑️", key=f"de_{e['id']}", help=t("Borrar")):
                desactivar_estimacion(sesion["user_id"], e["id"])
                st.rerun()
        with st.form("frm_estim"):
            c1, c2 = st.columns(2)
            cn_e   = c1.text_input(t("Concepto"), placeholder="Comida",
                                    autocomplete="off")
            mo_e   = c2.number_input(t("Promedio (€)"), min_value=0.01,
                                      value=None, placeholder="ej: 200.00", step=10.0)
            if st.form_submit_button(t("Agregar"), width="stretch"):
                if mo_e is None:
                    st.error(t("Introduce un monto."))
                elif cn_e:
                    guardar_estimacion(sesion["user_id"], cn_e, mo_e)
                    st.rerun()

    with cfg4:
        st.subheader(t("Provisiones anuales"))
        st.caption(t("Seguro, ITV... se divide entre 12 y se reserva cada mes."))
        for p in obtener_provisiones(sesion["user_id"]):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(p["concepto"])
            c2.write(f"€{p['monto_anual']:.2f}/año")
            c3.write(f"€{p['cuota_mes']:.2f}/mes")
            if c4.button("🗑️", key=f"dp_{p['id']}", help=t("Borrar")):
                desactivar_provision(sesion["user_id"], p["id"])
                st.rerun()
        with st.form("frm_prov"):
            c1, c2 = st.columns(2)
            cn_p   = c1.text_input(t("Concepto"), placeholder="Seguro carro",
                                    autocomplete="off")
            mo_an  = c2.number_input(t("Monto anual (€)"), min_value=0.01,
                                      value=None, placeholder="ej: 600.00", step=50.0)
            if mo_an:
                st.caption(t("Reserva mensual: **€{amount:.2f}**", amount=mo_an / 12))
            if st.form_submit_button(t("Agregar"), width="stretch"):
                if mo_an is None:
                    st.error(t("Introduce un monto."))
                elif cn_p:
                    guardar_provision(sesion["user_id"], cn_p, mo_an)
                    st.rerun()
