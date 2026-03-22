import sqlite3
from contextlib import contextmanager

DB_PATH = "finanzas.db"


# ─────────────────────────────────────────
# CONEXIÓN — context manager
# ─────────────────────────────────────────

@contextmanager
def get_db():
    """
    Abre la conexión, la entrega al bloque with,
    hace commit si todo salió bien, rollback si hubo error,
    y cierra siempre al final.

    Uso:
        with get_db() as conn:
            conn.execute(...)
        # conn cerrada automáticamente aquí
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn          # entrega la conexión al bloque with
        conn.commit()       # si no hubo error → confirma cambios
    except Exception:
        conn.rollback()     # si hubo error → deshace cambios
        raise               # re-lanza el error para que se vea
    finally:
        conn.close()        # siempre cierra, pase lo que pase


# ─────────────────────────────────────────
# CREAR TABLAS
# ─────────────────────────────────────────

def crear_tablas():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre     TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                password   TEXT NOT NULL,
                pct_ahorro REAL NOT NULL DEFAULT 0.70
                               CHECK(pct_ahorro > 0 AND pct_ahorro < 1),
                creado     DATE DEFAULT (date('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingresos (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                fecha    DATE NOT NULL,
                concepto TEXT NOT NULL,
                monto    REAL NOT NULL,
                tipo     TEXT NOT NULL CHECK(tipo IN ('sueldo', 'extra')),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gastos_generales (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                fecha     DATE NOT NULL,
                concepto  TEXT NOT NULL,
                monto     REAL NOT NULL,
                categoria TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gastos_casa (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                fecha      DATE NOT NULL,
                concepto   TEXT NOT NULL,
                monto      REAL NOT NULL,
                recurrente BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gastos_importantes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                fecha     DATE NOT NULL,
                concepto  TEXT NOT NULL,
                monto     REAL NOT NULL,
                prioridad TEXT DEFAULT 'media',
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_gastos_fijos (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                concepto TEXT NOT NULL,
                monto    REAL NOT NULL,
                activo   BOOLEAN DEFAULT 1,
                UNIQUE(user_id, concepto),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_estimaciones (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                concepto TEXT NOT NULL,
                promedio REAL NOT NULL,
                activo   BOOLEAN DEFAULT 1,
                UNIQUE(user_id, concepto),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_provisiones (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                concepto    TEXT NOT NULL,
                monto_anual REAL NOT NULL,
                activo      BOOLEAN DEFAULT 1,
                UNIQUE(user_id, concepto),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)


        conn.execute("""
            CREATE TABLE IF NOT EXISTS cierre_mes (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           INTEGER NOT NULL,
                mes               TEXT NOT NULL,
                ahorro_mes        REAL DEFAULT 0,
                sobrante_sugerido REAL DEFAULT 0,
                sobrante_movido   REAL DEFAULT 0,
                ahorro_total_mes  REAL DEFAULT 0,
                UNIQUE(user_id, mes),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)




# ─────────────────────────────────────────
# CRUD USUARIOS
# ─────────────────────────────────────────

def crear_usuario(nombre, email, password_hash):
    """Devuelve True si exitoso, False si el email ya existe."""
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)",
                (nombre, email, password_hash)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def obtener_usuario(email):
    """Devuelve la fila como dict, o None si no existe."""
    with get_db() as conn:
        fila = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
    return dict(fila) if fila else None


# ─────────────────────────────────────────
# PORCENTAJE DE AHORRO
# ─────────────────────────────────────────

def obtener_pct_ahorro(user_id):
    """Devuelve (pct_ahorro, pct_ocio). Ej: (0.70, 0.30)"""
    with get_db() as conn:
        fila = conn.execute(
            "SELECT pct_ahorro FROM usuarios WHERE id = ?", (user_id,)
        ).fetchone()
    pct_ahorro = fila["pct_ahorro"] if fila else 0.70
    pct_ocio   = round(1 - pct_ahorro, 2)
    return pct_ahorro, pct_ocio


def actualizar_pct_ahorro(user_id, pct_ahorro):
    """Devuelve True si exitoso, False si valor inválido."""
    if not (0.01 <= pct_ahorro <= 0.99):
        return False
    with get_db() as conn:
        conn.execute(
            "UPDATE usuarios SET pct_ahorro = ? WHERE id = ?",
            (round(pct_ahorro, 2), user_id)
        )
    return True