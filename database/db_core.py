import os
import sqlite3
import sys
from contextlib import contextmanager
from urllib.parse import quote

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
FORCE_SQLITE = os.getenv("FORCE_SQLITE", "").strip().lower() in ("1", "true", "yes", "on")
USE_POSTGRES = bool(DATABASE_URL) and not FORCE_SQLITE
DB_PATH = "finanzas.db"

@st.cache_resource
def _get_postgres_pool(dsn: str) -> SimpleConnectionPool:
    """Pool de conexiones Postgres cacheado y reutilizable entre reruns."""
    return SimpleConnectionPool(1, 10, dsn)


@st.cache_resource
def _get_sqlite_connection():
    """Conexión SQLite cacheada para reducir el coste de reapertura."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _normalize_database_url(url: str) -> str:
    if not url:
        return url

    url = url.strip()
    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()

    if "://" not in url:
        return url

    scheme, rest = url.split("://", 1)
    if scheme not in ("postgresql", "postgres"):
        return url
    scheme = "postgresql"

    if "@" not in rest:
        return url

    creds, host_part = rest.rsplit("@", 1)
    if ":" not in creds:
        return url

    user, password = creds.split(":", 1)
    if password.startswith("[") and password.endswith("]"):
        password = password[1:-1]

    user = quote(user, safe="")
    password = quote(password, safe="")

    if "sslmode=" not in host_part.lower():
        if "?" in host_part:
            host_part += "&sslmode=require"
        else:
            host_part += "?sslmode=require"

    return f"{scheme}://{user}:{password}@{host_part}"


def _sqlite_default_date():
    return "(date('now'))"


def _postgres_default_date():
    return "(CURRENT_DATE::text)"


def _sqlite_default_timestamp():
    return "(strftime('%Y-%m-%d %H:%M:%f', 'now'))"


def _postgres_default_timestamp():
    return "(to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS.MS'))"


def _integer_pk():
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _boolean_default(value: bool):
    if USE_POSTGRES:
        return "TRUE" if value else "FALSE"
    return "1" if value else "0"


class PostgresConnection:
    def __init__(self, conn):
        self._conn = conn
        self._cursor = conn.cursor(cursor_factory=RealDictCursor)

    def execute(self, sql, params=None):
        params = params or ()
        if isinstance(sql, str):
            sql = sql.replace("?", "%s")
        self._cursor.execute(sql, tuple(params))
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._cursor.close()
        self._conn.close()


@contextmanager
def get_db():
    """
    Abre la conexión a SQLite local o una conexión Postgres desde pool.

    Usa @st.cache_resource para mantener el pool / la conexión viva entre reruns.
    En caso de fallo de conexión remota, intenta limpiar el recurso cacheado y reconectar.
    """
    if USE_POSTGRES:
        dsn = _normalize_database_url(DATABASE_URL)
        try:
            pool = _get_postgres_pool(dsn)
            conn = pool.getconn()
        except (psycopg2.OperationalError, psycopg2.InterfaceError, Exception) as exc:
            # Reconectar si la sesión remota caducó o el pool quedó inválido.
            try:
                _get_postgres_pool.clear()
            except Exception:
                pass
            pool = _get_postgres_pool(dsn)
            conn = pool.getconn()
        db = PostgresConnection(conn)
    else:
        conn = _get_sqlite_connection()
        db = conn

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if USE_POSTGRES:
            db._cursor.close()
            pool.putconn(conn)
        # SQLite usa conexión cacheada; no se cierra aquí.


# ─────────────────────────────────────────
# CREAR TABLAS
# ─────────────────────────────────────────

@st.cache_resource
def crear_tablas():
    with get_db() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS usuarios (
                id         {_integer_pk()},
                nombre     TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                password   TEXT NOT NULL,
                pct_ahorro REAL NOT NULL DEFAULT 0.70
                               CHECK(pct_ahorro > 0 AND pct_ahorro < 1),
                creado     TEXT DEFAULT {_postgres_default_date() if USE_POSTGRES else _sqlite_default_date()}
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS ingresos (
                id       {_integer_pk()},
                user_id  INTEGER NOT NULL,
                fecha    TEXT NOT NULL,
                concepto TEXT NOT NULL,
                monto    REAL NOT NULL,
                tipo     TEXT NOT NULL CHECK(tipo IN ('sueldo', 'extra')),
                creado_en TEXT DEFAULT {_postgres_default_timestamp() if USE_POSTGRES else _sqlite_default_timestamp()},
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS gastos_generales (
                id        {_integer_pk()},
                user_id   INTEGER NOT NULL,
                fecha     TEXT NOT NULL,
                concepto  TEXT NOT NULL,
                monto     REAL NOT NULL,
                categoria TEXT NOT NULL,
                creado_en TEXT DEFAULT {_postgres_default_timestamp() if USE_POSTGRES else _sqlite_default_timestamp()},
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS gastos_casa (
                id         {_integer_pk()},
                user_id    INTEGER NOT NULL,
                fecha      TEXT NOT NULL,
                concepto   TEXT NOT NULL,
                monto      REAL NOT NULL,
                recurrente BOOLEAN DEFAULT {_boolean_default(True)},
                creado_en  TEXT DEFAULT {_postgres_default_timestamp() if USE_POSTGRES else _sqlite_default_timestamp()},
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS gastos_importantes (
                id        {_integer_pk()},
                user_id   INTEGER NOT NULL,
                fecha     TEXT NOT NULL,
                concepto  TEXT NOT NULL,
                monto     REAL NOT NULL,
                prioridad TEXT DEFAULT 'media',
                creado_en TEXT DEFAULT {_postgres_default_timestamp() if USE_POSTGRES else _sqlite_default_timestamp()},
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS config_gastos_fijos (
                id       {_integer_pk()},
                user_id  INTEGER NOT NULL,
                concepto TEXT NOT NULL,
                monto    REAL NOT NULL,
                activo   BOOLEAN DEFAULT {_boolean_default(True)},
                UNIQUE(user_id, concepto),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS config_estimaciones (
                id       {_integer_pk()},
                user_id  INTEGER NOT NULL,
                concepto TEXT NOT NULL,
                promedio REAL NOT NULL,
                activo   BOOLEAN DEFAULT {_boolean_default(True)},
                UNIQUE(user_id, concepto),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS config_plazos (
                id          {_integer_pk()},
                user_id     INTEGER NOT NULL,
                concepto    TEXT NOT NULL,
                monto_total REAL NOT NULL,
                meses       INTEGER NOT NULL CHECK(meses > 0),
                inicio_mes  TEXT NOT NULL,
                activo      BOOLEAN DEFAULT {_boolean_default(True)},
                UNIQUE(user_id, concepto, inicio_mes),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )
        """)


        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS cierre_mes (
                id                {_integer_pk()},
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

        _asegurar_columna_creado_en(conn, "ingresos")
        _asegurar_columna_creado_en(conn, "gastos_generales")
        _asegurar_columna_creado_en(conn, "gastos_casa")
        _asegurar_columna_creado_en(conn, "gastos_importantes")
        _rellenar_creado_en_si_falta(conn, "ingresos")
        _rellenar_creado_en_si_falta(conn, "gastos_generales")
        _rellenar_creado_en_si_falta(conn, "gastos_casa")
        _rellenar_creado_en_si_falta(conn, "gastos_importantes")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingresos_user_fecha ON ingresos(user_id, fecha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingresos_user_creado_en ON ingresos(user_id, creado_en)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_generales_user_fecha ON gastos_generales(user_id, fecha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_generales_user_creado_en ON gastos_generales(user_id, creado_en)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_casa_user_fecha ON gastos_casa(user_id, fecha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_casa_user_creado_en ON gastos_casa(user_id, creado_en)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_importantes_user_fecha ON gastos_importantes(user_id, fecha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_importantes_user_creado_en ON gastos_importantes(user_id, creado_en)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_config_gastos_fijos_user_activo ON config_gastos_fijos(user_id, activo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_config_estimaciones_user_activo ON config_estimaciones(user_id, activo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_config_plazos_user_activo ON config_plazos(user_id, activo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cierre_mes_user_mes ON cierre_mes(user_id, mes)")


def _asegurar_columna_creado_en(conn, tabla: str):
    if _existe_columna(conn, tabla, "creado_en"):
        return
    default_sql = _postgres_default_timestamp() if USE_POSTGRES else _sqlite_default_timestamp()
    conn.execute(f"ALTER TABLE {tabla} ADD COLUMN creado_en TEXT DEFAULT {default_sql}")


def _existe_columna(conn, tabla: str, columna: str) -> bool:
    if USE_POSTGRES:
        fila = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            """,
            (tabla, columna),
        ).fetchone()
    else:
        fila = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
        return any(col["name"] == columna for col in fila)
    return fila is not None


def _rellenar_creado_en_si_falta(conn, tabla: str):
    conn.execute(
        f"UPDATE {tabla} "
        "SET creado_en = CASE "
        "WHEN creado_en IS NULL OR creado_en = '' THEN fecha || ' 00:00:00.000' "
        "ELSE creado_en END "
        "WHERE creado_en IS NULL OR creado_en = ''"
    )




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
        st.cache_data.clear()
        return True
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return False


@st.cache_data(ttl=600)
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

@st.cache_data(ttl=600)
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
    st.cache_data.clear()
    return True
