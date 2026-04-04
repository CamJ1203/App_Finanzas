import streamlit as st


DEFAULT_LANGUAGE = "es"
SUPPORTED_LANGUAGES = {"es", "en"}
LANGUAGE_LABELS = {"es": "Español", "en": "English"}


TRANSLATIONS = {
    "en": {
        "Mis Finanzas": "My Finances",
        "Gestiona tu dinero con inteligencia": "Manage your money intelligently",
        "Iniciar sesión": "Sign in",
        "Crear cuenta": "Create account",
        "Bienvenido de nuevo": "Welcome back",
        "Email": "Email",
        "Contraseña": "Password",
        "Mantener sesión abierta en este dispositivo": "Keep me signed in on this device",
        "Tu sesión quedará guardada durante {days} días.": "Your session will stay saved for {days} days.",
        "Entrar": "Sign in",
        "Completa todos los campos.": "Complete all fields.",
        "No existe una cuenta con ese email.": "No account exists with that email.",
        "Contraseña incorrecta.": "Incorrect password.",
        "Bienvenido, {name}!": "Welcome, {name}!",
        "Crea tu cuenta": "Create your account",
        "Nombre": "Name",
        "Confirmar contraseña": "Confirm password",
        "¿Qué % quieres ahorrar?": "What % do you want to save?",
        "Ahorro: **{save}%** · Ocio: **{fun}%**": "Savings: **{save}%** · Fun: **{fun}%**",
        "Las contraseñas no coinciden.": "Passwords do not match.",
        "La contraseña debe tener al menos 6 caracteres.": "Password must be at least 6 characters.",
        "Ese email ya tiene una cuenta registrada.": "That email already has an account.",
        "Cuenta creada. Bienvenido, {name}!": "Account created. Welcome, {name}!",
        "Distribución del remanente": "Remaining balance distribution",
        "Se aplica sobre el remanente después de gastos previstos.": "Applied to what remains after planned expenses.",
        "% de ahorro": "% to save",
        "Ahorro": "Savings",
        "Ocio": "Fun",
        "Imprevistos": "Unexpected",
        "Guardar cambio": "Save change",
        "Porcentaje actualizado.": "Percentage updated.",
        "Valor inválido.": "Invalid value.",
        "Selecciona el mes activo": "Select the active month",
        "Mes": "Month",
        "Año": "Year",
        "🔒 {month} cerrado": "🔒 {month} closed",
        "🟢 {month} activo": "🟢 {month} active",
        "🎯 Ahorro total": "🎯 Total savings",
        "🎉 Ocio total restante": "🎉 Total fun remaining",
        "🚪 Cerrar sesión": "🚪 Sign out",
        "Registrar ingreso": "Record income",
        "Tipo": "Type",
        "Sueldo": "Salary",
        "Extra": "Extra",
        "Fecha": "Date",
        "Monto (€)": "Amount (€)",
        "Concepto": "Description",
        "Guardar": "Save",
        "Introduce un monto.": "Enter an amount.",
        "Escribe un concepto.": "Enter a description.",
        "Ingreso de €{amount:.2f} registrado.": "Income of €{amount:.2f} recorded.",
        "Vista previa de distribución:": "Distribution preview:",
        "Remanente": "Remaining",
        "Gasto de ocio": "Fun expense",
        "Ropa, dulces, comida callejera, entretenimiento, salidas...": "Clothes, sweets, street food, entertainment, going out...",
        "Gasto de ocio registrado.": "Fun expense recorded.",
        "Gasto imprevisto importante": "Major unexpected expense",
        "Sale del remanente, reduciendo ahorro y ocio proporcionalmente.": "It comes out of the remaining balance, reducing savings and fun proportionally.",
        "Registrado. Reduce ahorro €{save:.2f} · ocio €{fun:.2f}": "Recorded. Reduces savings by €{save:.2f} · fun by €{fun:.2f}",
        "Gastos fijos": "Fixed expenses",
        "Arriendo, luz, agua, internet... Elige la categoría del previsto.": "Rent, electricity, water, internet... Choose the planned category.",
        "Categoría prevista": "Planned category",
        "Otro": "Other",
        "Gasto fijo registrado en '{category}'.": "Fixed expense recorded in '{category}'.",
        "📊 Resumen": "📊 Summary",
        "➕ Ingresar": "➕ Add",
        "📋 Historial": "📋 History",
        "🔒 Cierre": "🔒 Close month",
        "⚙️ Config": "⚙️ Settings",
        "Resumen — {month}": "Summary — {month}",
        "Estado del mes": "Month status",
        "💵 Ingresos": "💵 Income",
        "💵 Ingresos_label": "💵 Income",
        "Ingresos": "Income",
        "📦 Gastos del Mes": "📦 Monthly expenses",
        "💾 Ahorro mensual": "💾 Monthly savings",
        "🎉 Ocio disponible": "🎉 Fun available",
        "Total": "Total",
        "Extras": "Extras",
        "📋 Plan del mes": "📋 Plan for the month",
        "Previstos configurados vs lo que has gastado en gastos fijos este mes.": "Configured plans vs what you spent on fixed expenses this month.",
        "Fijo": "Fixed",
        "Estimación": "Estimate",
        "Provisión /12": "Provision /12",
        "Concepto_col": "Description",
        "Tipo_col": "Type",
        "Previsto": "Planned",
        "Gastado": "Spent",
        "Diferencia": "Difference",
        "Estado": "Status",
        "✅ Dentro": "✅ Within",
        "⚠️ Excedido": "⚠️ Exceeded",
        "Total previstos": "Total planned",
        "Total gastado": "Total spent",
        "€{amount:.2f} restante": "€{amount:.2f} remaining",
        "€{amount:.2f} excedido": "€{amount:.2f} exceeded",
        "No tienes gastos configurados. Ve a ⚙️ Config para agregar fijos, estimaciones o provisiones.": "You have no configured expenses. Go to ⚙️ Settings to add fixed expenses, estimates, or provisions.",
        "📅 Histórico del año": "📅 Year history",
        "Sin datos este año.": "No data this year.",
        "Ingresar datos": "Add data",
        "🔒 El mes {month} está cerrado. Ve a 'Cierre' para desbloquearlo.": "🔒 The month {month} is closed. Go to 'Close month' to unlock it.",
        "💼 Ingresos": "💼 Income",
        "🛒 Ocio": "🛒 Fun",
        "⚠️ Imprevisto": "⚠️ Unexpected",
        "🏠 Gastos fijos": "🏠 Fixed expenses",
        "Historial — {month}": "History — {month}",
        "Imprevistos + Gastos fijos": "Unexpected + Fixed expenses",
        "Todos los movimientos": "All transactions",
        "Total: €{amount:.2f}": "Total: €{amount:.2f}",
        "Sin ingresos este mes.": "No income this month.",
        "Total ocio: €{amount:.2f}": "Total fun: €{amount:.2f}",
        "Sin gastos de ocio este mes.": "No fun expenses this month.",
        "⚠️ Imprevistos importantes": "⚠️ Major unexpected expenses",
        "Total imprevistos: €{amount:.2f}": "Total unexpected: €{amount:.2f}",
        "🏠 Gastos fijos_label": "🏠 Fixed expenses",
        "Total gastos fijos: €{amount:.2f}": "Total fixed expenses: €{amount:.2f}",
        "Sin imprevistos ni gastos fijos este mes.": "No unexpected or fixed expenses this month.",
        "Sin movimientos este mes.": "No transactions this month.",
        "Cierre de mes — {month}": "Month close — {month}",
        "✅ El mes {month} está cerrado.": "✅ The month {month} is closed.",
        "Ocio gastado": "Fun spent",
        "Desbloquear elimina el cierre — podrás volver a editar datos.": "Unlocking removes the close so you can edit data again.",
        "🔓 Desbloquear mes para editar": "🔓 Unlock month for editing",
        "Mes desbloqueado.": "Month unlocked.",
        "Resumen antes de cerrar": "Summary before closing",
        "Gastos fijos €": "Fixed expenses €",
        "🎉 Ocio disponible rest.": "🎉 Remaining fun available",
        "Sobrante de gastos previstos": "Remaining planned-expense balance",
        "Te sobran **€{amount:.2f}** de los gastos previstos.": "You have **€{amount:.2f}** left from planned expenses.",
        "¿Dónde mover el sobrante?": "Where should the remainder go?",
        "Sumar al ahorro": "Add to savings",
        "Sumar al ocio": "Add to fun",
        "Dividir (50/50)": "Split (50/50)",
        "Ahorro final: €{save:.2f} · Ocio final: €{fun:.2f}": "Final savings: €{save:.2f} · Final fun: €{fun:.2f}",
        "Sin sobrante de previstos este mes.": "No planned-expense remainder this month.",
        "✅ Confirmar y cerrar el mes": "✅ Confirm and close the month",
        "✅ Mes cerrado. Ahorro: **€{amount:.2f}**": "✅ Month closed. Savings: **€{amount:.2f}**",
        "Configuración": "Settings",
        "💰 % Ahorro": "💰 % Savings",
        "🛒 Estimaciones": "🛒 Estimates",
        "📆 Provisiones": "📆 Provisions",
        "📅 Provisiones": "📅 Provisions",
        "Se aplica sobre lo que sobra después de restar los gastos previstos.": "Applied to what remains after subtracting planned expenses.",
        "Gastos fijos mensuales": "Monthly fixed expenses",
        "Arriendo, servicios... se restan cada mes antes de calcular el ahorro.": "Rent, utilities... subtracted each month before calculating savings.",
        "Agregar": "Add",
        "Estimaciones mensuales": "Monthly estimates",
        "Comida, gasolina... promedios variables que reservas cada mes.": "Food, gas... variable averages you set aside each month.",
        "Promedio (€)": "Average (€)",
        "Provisiones anuales": "Annual provisions",
        "Seguro, ITV... se divide entre 12 y se reserva cada mes.": "Insurance, inspections... divided by 12 and set aside each month.",
        "Monto anual (€)": "Annual amount (€)",
        "Reserva mensual: **€{amount:.2f}**": "Monthly reserve: **€{amount:.2f}**",
        "Editar": "Edit",
        "Borrar": "Delete",
        "Cancelar": "Cancel",
    }
}


MONTH_ABBR = {
    "es": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}


def _normalize_language(locale_value: str | None) -> str:
    if not locale_value:
        return DEFAULT_LANGUAGE
    base = locale_value.replace("_", "-").split("-")[0].lower()
    return base if base in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def _browser_language() -> str:
    locale = getattr(st.context, "locale", None)
    if not locale:
        headers = getattr(st.context, "headers", None)
        if headers:
            locale = headers.get("Accept-Language")
    return _normalize_language(locale)


def get_language() -> str:
    query_lang = st.query_params.get("lang")
    if query_lang:
        language = _normalize_language(query_lang)
        st.session_state["lang"] = language
        st.session_state["lang_source"] = "query"
        return language

    if st.session_state.get("lang_source") == "manual" and "lang" in st.session_state:
        return st.session_state["lang"]

    language = _browser_language()
    st.session_state["lang"] = language
    st.session_state["lang_source"] = "browser"
    return language


def set_language(language: str):
    language = _normalize_language(language)
    st.session_state["lang"] = language
    st.session_state["lang_source"] = "manual"
    st.query_params["lang"] = language


def clear_language_override():
    st.session_state["lang"] = _browser_language()
    st.session_state["lang_source"] = "browser"
    try:
        del st.query_params["lang"]
    except KeyError:
        pass


def t(text: str, **kwargs) -> str:
    language = get_language()
    translated = TRANSLATIONS.get(language, {}).get(text, text)
    if kwargs:
        return translated.format(**kwargs)
    return translated


def month_abbr(month_number: int) -> str:
    language = get_language()
    names = MONTH_ABBR.get(language, MONTH_ABBR[DEFAULT_LANGUAGE])
    return names[month_number - 1]


def language_options() -> list[str]:
    return list(LANGUAGE_LABELS.keys())


def language_label(language: str) -> str:
    return LANGUAGE_LABELS.get(language, language)
