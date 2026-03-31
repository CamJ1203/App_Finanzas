# 💰 App de Finanzas Personales

Llevo 4 años usando un Excel para gestionar mis finanzas. Lo fui mejorando poco a poco — añadiendo fórmulas, categorías, hojas nuevas — hasta que llegó un punto en el que el Excel hacía exactamente lo que yo quería, pero se había vuelto difícil de mantener y no podía usarlo cómodamente desde el móvil ni compartirlo con familia.

Así que decidí convertirlo en una app real.

Este proyecto es esa conversión. La lógica es la misma que perfeccioné durante 4 años en Excel, pero ahora en Python con una interfaz web que funciona en cualquier dispositivo.

## Cómo funciona

La idea central es simple: el dinero se planifica **antes** de gastarlo, desde el dia 1 ya sabes cual es el ingreso minimo, y en base a eso gestionas tu dinero.

---------
INGRESOS
  − Gastos previstos (arriendo, comida, gasolina, seguros...)
  = REMANENTE
      × % ahorro  →  Ahorro protegido o Invertido
      × % ocio    →  Dinero libre
---------

Los gastos imprevistos (médico, reparación, algo inesperado) reducen el ahorro. Al cerrar el mes, lo que sobró de los previstos se puede mover al ahorro o al ocio.

---

## Qué puedes hacer

- Registrar ingresos (sueldo y extras)
- Configurar gastos fijos, estimaciones mensuales y provisiones anuales
- Ver en tiempo real cuánto te queda de ahorro y de ocio
- Comparar lo previsto con lo realmente gastado
- Cerrar cada mes y decidir qué hacer con el sobrante
- Ver el histórico del año
- Sesión persistente con tokens JWT — no tienes que hacer login cada vez
- Funciona en PC, móvil y tablet
- Llevar un control total de tu vida financiera, generando ese estado de paz que pase lo que pase sabes el porque.

---

## Stack

- **Python** — lógica y backend
- **SQLite** — base de datos local (un solo archivo)
- **Postsql** - base de datos en la nube
- **Streamlit** — interfaz web
- **PyJWT** — autenticación con tokens seguros

---

## Instalación local

```bash
git clone https://github.com/tu-usuario/app-finanzas.git
cd app-finanzas

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

cp .env.example .env
# Editar .env y poner tu FINANZAS_SECRET

streamlit run app.py
```

---

## Variables de entorno

| Variable | Descripción |
|---|---|
| `FINANZAS_SECRET` | Clave para firmar tokens JWT de sesión |

---

## Estructura

```
app-finanzas/
├── app.py              # Interfaz principal (Streamlit)
├── auth.py             # Login, registro, tokens JWT
├── calculos.py         # Lógica financiera
├── requirements.txt
└── database/
    ├── db_core.py      # Conexión y tablas
    ├── db_ingresos.py  # CRUD ingresos
    ├── db_gastos.py    # CRUD gastos
    └── db_config.py    # Configuración mensual
```
Basado en un sistema de seguimiento de finanzas en Excel usado y perfeccionado durante 4 años.
