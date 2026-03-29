import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import quote

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
FORCE_SQLITE = os.getenv("FORCE_SQLITE", "").strip().lower() in ("1", "true", "yes", "on")
USE_POSTGRES = bool(DATABASE_URL) and not FORCE_SQLITE
DB_PATH = "finanzas.db"


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
    Abre la conexión a SQLite local o a Postgres/Supabase.

    - Si la variable de entorno DATABASE_URL está configurada y FORCE_SQLITE no está activado,
      usa esa conexión Postgres.
    - Si no, usa el archivo local finanzas.db.
    """
    if USE_POSTGRES:
        dsn = _normalize_database_url(DATABASE_URL)
        try:
            conn = psycopg2.connect(dsn, sslmode="require")
        except Exception as exc:
            raise RuntimeError(
                "Fallo de conexión a Postgres. Verifica DATABASE_URL en los secretos y que el servidor permita SSL."
            ) from exc
        db = PostgresConnection(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        db = conn

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ─────────────────────────────────────────
# CREAR TABLAS
# ─────────────────────────────────────────

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
            CREATE TABLE IF NOT EXISTS config_provisiones (
                id          {_integer_pk()},
                user_id     INTEGER NOT NULL,
                concepto    TEXT NOT NULL,
                monto_anual REAL NOT NULL,
                activo      BOOLEAN DEFAULT {_boolean_default(True)},
                UNIQUE(user_id, concepto),
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
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
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