import hashlib
import jwt
import os
import streamlit as st
from datetime import datetime, timedelta, timezone

from database import (
    crear_usuario,
    obtener_usuario,
    actualizar_pct_ahorro,
    obtener_pct_ahorro,
    get_db,
)
from i18n import (
    t,
    get_language,
    set_language,
    clear_language_override,
    language_options,
    language_label,
)

# ─────────────────────────────────────────
# CLAVE SECRETA
# Se lee desde variable de entorno para no
# exponerla en el código ni en GitHub.
#
# Local:  crea un archivo .env con:
#         FINANZAS_SECRET=tu-clave-aqui
#
# Streamlit Cloud: ponla en
#         Settings → Secrets → FINANZAS_SECRET
# ─────────────────────────────────────────

CLAVE_SECRETA = os.environ.get(
    "FINANZAS_SECRET",
    "dev-local-insegura-cambiar-en-produccion"   # solo para desarrollo local
)
DIAS_SESION = 30


# ─────────────────────────────────────────
# CONTRASEÑAS
# ─────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _verificar(password_input: str, hash_guardado: str) -> bool:
    return _hash(password_input) == hash_guardado


# ─────────────────────────────────────────
# TOKENS JWT
# ─────────────────────────────────────────

def _crear_token(user_id: int) -> str:
    """
    Crea un token JWT con el user_id encriptado.
    El token expira en DIAS_SESION días.
    """
    payload = {
        "uid": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=DIAS_SESION),
        "iat": datetime.now(timezone.utc),  # fecha de emisión
    }
    return jwt.encode(payload, CLAVE_SECRETA, algorithm="HS256")

def _verificar_token(token: str) -> int | None:
    """
    Verifica el token y devuelve el user_id si es válido.
    Devuelve None si el token es inválido o expiró.
    """
    try:
        payload = jwt.decode(token, CLAVE_SECRETA, algorithms=["HS256"])
        return payload.get("uid")
    except jwt.ExpiredSignatureError:
        # Token expirado — limpiar y pedir login de nuevo
        st.query_params.clear()
        return None
    except jwt.InvalidTokenError:
        # Token manipulado o inválido — limpiar
        st.query_params.clear()
        return None


# ─────────────────────────────────────────
# SESIÓN
# ─────────────────────────────────────────

CLAVES_SESION = ["user_id", "nombre", "email", "pct_ahorro", "pct_ocio"]

def hay_sesion() -> bool:
    return all(k in st.session_state for k in CLAVES_SESION)

def obtener_sesion() -> dict:
    if not hay_sesion():
        return {}
    return {
        "user_id":    st.session_state["user_id"],
        "nombre":     st.session_state["nombre"],
        "email":      st.session_state["email"],
        "pct_ahorro": st.session_state["pct_ahorro"],
        "pct_ocio":   st.session_state["pct_ocio"],
    }

def _iniciar_sesion(usuario: dict):
    pct_ahorro, pct_ocio = obtener_pct_ahorro(usuario["id"])
    st.session_state["user_id"]    = usuario["id"]
    st.session_state["nombre"]     = usuario["nombre"]
    st.session_state["email"]      = usuario["email"]
    st.session_state["pct_ahorro"] = pct_ahorro
    st.session_state["pct_ocio"]   = pct_ocio

@st.cache_data(ttl=600)
def _obtener_usuario_por_id(user_id: int) -> dict | None:
    with get_db() as conn:
        fila = conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(fila) if fila else None

def cerrar_sesion():
    """Limpia sesión y elimina el token de la URL."""
    for key in CLAVES_SESION:
        st.session_state.pop(key, None)
    st.query_params.clear()
    st.rerun()


# ─────────────────────────────────────────
# RECUPERAR SESIÓN DESDE TOKEN
# ─────────────────────────────────────────

def intentar_sesion_guardada() -> bool:
    """
    Lee el token JWT de la URL, lo verifica,
    y restaura la sesión si es válido.
    Devuelve True si la sesión fue restaurada.
    """
    token = st.query_params.get("token", None)
    if not token:
        return False

    user_id = _verificar_token(token)
    if not user_id:
        return False

    usuario = _obtener_usuario_por_id(user_id)
    if not usuario:
        st.query_params.clear()
        return False

    _iniciar_sesion(usuario)
    return True


# ─────────────────────────────────────────
# PANTALLA DE AUTH
# ─────────────────────────────────────────

def pantalla_auth():
    """
    Intenta restaurar sesión desde token.
    Si no hay token válido, muestra login/registro.
    """
    if intentar_sesion_guardada():
        st.rerun()
        return

    c_lang_1, c_lang_2, c_lang_3 = st.columns([2, 1, 1])
    selected_lang = c_lang_1.selectbox(
        "Language",
        language_options(),
        index=language_options().index(get_language()),
        format_func=language_label,
        key="auth_language_select",
    )
    if c_lang_2.button("Apply", width="stretch"):
        set_language(selected_lang)
        st.rerun()
    if c_lang_3.button("Auto", width="stretch"):
        clear_language_override()
        st.rerun()

    st.title(f"💰 {t('Mis Finanzas')}")
    st.caption(t("Gestiona tu dinero con inteligencia"))
    st.divider()

    tab_login, tab_registro = st.tabs([t("Iniciar sesión"), t("Crear cuenta")])
    with tab_login:
        _formulario_login()
    with tab_registro:
        _formulario_registro()


def _formulario_login():
    st.subheader(t("Bienvenido de nuevo"))

    with st.form("form_login"):
        email = st.text_input(t("Email"), placeholder="tu@email.com")
        password = st.text_input(t("Contraseña"), type="password")
        recordar = st.checkbox(
            t("Mantener sesión abierta en este dispositivo"),
            value=True,
            help=t("Tu sesión quedará guardada durante {days} días.", days=DIAS_SESION)
        )
        btn = st.form_submit_button(t("Entrar"), width="stretch")

    if btn:
        if not email or not password:
            st.error(t("Completa todos los campos."))
            return

        usuario = obtener_usuario(email.strip().lower())
        if usuario is None:
            st.error(t("No existe una cuenta con ese email."))
            return
        if not _verificar(password, usuario["password"]):
            st.error(t("Contraseña incorrecta."))
            return

        _iniciar_sesion(usuario)

        if recordar:
            # Guardar token JWT firmado en la URL
            st.query_params["token"] = _crear_token(usuario["id"])
        else:
            st.query_params.clear()

        st.success(t("Bienvenido, {name}!", name=usuario["nombre"]))
        st.rerun()


def _formulario_registro():
    st.subheader(t("Crea tu cuenta"))

    with st.form("form_registro"):
        nombre = st.text_input(t("Nombre"), placeholder="Camilo")
        email = st.text_input(t("Email"), placeholder="tu@email.com")
        password = st.text_input(t("Contraseña"), type="password")
        password_conf = st.text_input(t("Confirmar contraseña"), type="password")
        pct_ahorro = st.slider(
            t("¿Qué % quieres ahorrar?"),
            min_value=10, max_value=90, value=70, step=5, format="%d%%"
        )
        recordar = st.checkbox(t("Mantener sesión abierta en este dispositivo"), value=True)
        btn = st.form_submit_button(t("Crear cuenta"), width="stretch")

    st.caption(t("Ahorro: **{save}%** · Ocio: **{fun}%**", save=pct_ahorro, fun=100 - pct_ahorro))

    if btn:
        if not nombre or not email or not password:
            st.error(t("Completa todos los campos."))
            return
        if password != password_conf:
            st.error(t("Las contraseñas no coinciden."))
            return
        if len(password) < 6:
            st.error(t("La contraseña debe tener al menos 6 caracteres."))
            return

        exito = crear_usuario(
            nombre=nombre.strip(),
            email=email.strip().lower(),
            password_hash=_hash(password),
        )
        if not exito:
            st.error(t("Ese email ya tiene una cuenta registrada."))
            return

        usuario = obtener_usuario(email.strip().lower())
        actualizar_pct_ahorro(usuario["id"], pct_ahorro / 100)
        _iniciar_sesion(usuario)

        if recordar:
            st.query_params["token"] = _crear_token(usuario["id"])

        st.success(t("Cuenta creada. Bienvenido, {name}!", name=nombre))
        st.rerun()


# ─────────────────────────────────────────
# WIDGET DE CONFIGURACIÓN
# ─────────────────────────────────────────

def widget_pct_ahorro():
    sesion     = obtener_sesion()
    pct_actual = int(sesion["pct_ahorro"] * 100)

    st.subheader(t("Distribución del remanente"))
    st.caption(t("Se aplica sobre el remanente después de gastos previstos."))

    nuevo_pct = st.slider(t("% de ahorro"), 10, 90, pct_actual, step=5, format="%d%%")
    c1, c2    = st.columns(2)
    c1.metric(t("Ahorro"), f"{nuevo_pct}%")
    c2.metric(t("Ocio"),   f"{100-nuevo_pct}%")

    if st.button(t("Guardar cambio"), width="stretch"):
        exito = actualizar_pct_ahorro(sesion["user_id"], nuevo_pct / 100)
        if exito:
            st.session_state["pct_ahorro"] = nuevo_pct / 100
            st.session_state["pct_ocio"]   = round(1 - nuevo_pct / 100, 2)
            st.success(t("Porcentaje actualizado."))
        else:
            st.error(t("Valor inválido."))
