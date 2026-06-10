"""
Модуль подключения к базе данных (SQLite или PostgreSQL).

Предоставляет контекстный менеджер для безопасной работы с БД.
"""
import sqlite3
import logging
import re
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь к файлу базы данных SQLite (используется как дефолт/fallback)
DB_PATH = Path(__file__).parent / "vpn_bot.db"

# Конфликтные ключи для перевода INSERT OR IGNORE -> ON CONFLICT
CONFLICT_TARGETS = {
    'settings': '(key)',
    'pages': '(page_key)',
    'tariffs': '(id)',
    'tariff_groups': '(id)',
    'referral_levels': '(level_number)',
    'server_groups': '(server_id, group_id)',
    'notification_log': '(vpn_key_id, sent_at)',
    'users': '(telegram_id)',
}


def translate_insert_or_ignore(sql: str) -> str:
    """Перевод синтаксиса INSERT OR IGNORE из SQLite в PostgreSQL ON CONFLICT DO NOTHING."""
    match = re.search(r'(?i)INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)', sql)
    if match:
        table_name = match.group(1).lower()
        sql = re.sub(r'(?i)\bINSERT\s+OR\s+IGNORE\s+INTO\b', 'INSERT INTO', sql)
        if table_name in CONFLICT_TARGETS:
            conflict_clause = f" ON CONFLICT {CONFLICT_TARGETS[table_name]} DO NOTHING"
            sql = sql.rstrip().rstrip(';') + conflict_clause
    return sql


class PostgresRow:
    """
    Адаптер для результатов PostgreSQL строк, полностью имитирующий sqlite3.Row.
    """
    def __init__(self, description, values):
        self._keys = [desc[0] for desc in description] if description else []
        self._values = values
        self._map = {k: i for i, k in enumerate(self._keys)}

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._values[item]
        if isinstance(item, str):
            if item in self._map:
                return self._values[self._map[item]]
            raise KeyError(item)
        raise TypeError("Index must be int or str")

    def get(self, key: str, default=None):
        if key in self._map:
            return self._values[self._map[key]]
        return default

    def keys(self):
        return self._keys

    def values(self):
        return self._values

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return f"Row({dict(zip(self._keys, self._values))})"


class PostgresCursor:
    """
    Обертка над курсором psycopg2 для поддержки sqlite3-подобного выполнения.
    """
    def __init__(self, raw_cursor, conn_wrapper):
        self._cursor = raw_cursor
        self._conn_wrapper = conn_wrapper
        self.lastrowid = None

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def _translate_sql(self, sql: str) -> str:
        """Переводит SQLite-специфичный SQL в диалект PostgreSQL."""
        # 0. Игнорирование SQLite PRAGMA
        if re.match(r'(?i)^\s*PRAGMA\b', sql):
            return "SELECT 1"

        # 1. ? -> %s
        translated = sql.replace('?', '%s')

        # 2. sqlite_master -> pg_tables
        translated = re.sub(
            r'(?i)\bsqlite_master\s+WHERE\s+type\s*=\s*\'table\'\s+AND\s+name\s*=\s*\'(\w+)\'',
            r"pg_tables WHERE schemaname='public' AND tablename='\1'",
            translated
        )
        translated = re.sub(r'(?i)\bsqlite_master\b', 'pg_tables', translated)
        translated = re.sub(
            r'(?i)\bSELECT\s+name\s+FROM\s+pg_tables\b',
            'SELECT tablename AS name FROM pg_tables',
            translated
        )

        # 3. datetime('now') -> NOW()
        translated = re.sub(r"(?i)\bdatetime\(\s*'now'\s*\)", "NOW()", translated)
        translated = re.sub(r"(?i)['\"]now['\"]", "NOW()", translated)

        # 4. datetime(expr, modifier) -> expr + modifier
        while True:
            new_translated = re.sub(
                r"(?i)\bdatetime\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
                r"(\1) + CAST(\2 AS INTERVAL)",
                translated
            )
            if new_translated == translated:
                break
            translated = new_translated

        # 5. MAX(datetime('now'), ...) -> GREATEST(NOW(), ...)
        translated = re.sub(r"(?i)\bMAX\(\s*NOW\(\)", "GREATEST(NOW()", translated)
        translated = re.sub(r"(?i)\bMAX\(\s*CURRENT_TIMESTAMP", "GREATEST(CURRENT_TIMESTAMP", translated)

        # 5.5 INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY
        translated = re.sub(
            r'(?i)\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b',
            'SERIAL PRIMARY KEY',
            translated
        )

        # 6. INSERT OR IGNORE -> ON CONFLICT
        translated = translate_insert_or_ignore(translated)

        return translated

    def execute(self, sql: str, parameters=None):
        translated_sql = self._translate_sql(sql)

        # Поддержка lastrowid: если это INSERT в таблицу с "id", дописываем RETURNING id
        is_insert = re.search(r'(?i)^\s*INSERT\s+', sql) is not None
        has_returning = re.search(r'(?i)\bRETURNING\b', translated_sql) is not None

        table_name = None
        if is_insert and not has_returning:
            match = re.search(r'(?i)INSERT\s+(?:OR\s+\w+\s+)?INTO\s+(\w+)', sql)
            if match:
                table_name = match.group(1).lower()

        should_return_id = is_insert and not has_returning and table_name not in ('settings', 'schema_version', 'server_groups')

        if should_return_id:
            translated_sql = translated_sql.rstrip().rstrip(';') + " RETURNING id"

        if parameters is not None:
            self._cursor.execute(translated_sql, parameters)
        else:
            self._cursor.execute(translated_sql)

        # Считываем возвращенный ID для имитации lastrowid
        if should_return_id:
            try:
                row = self._cursor.fetchone()
                if row:
                    self.lastrowid = row[0]
            except Exception:
                self.lastrowid = None
        else:
            self.lastrowid = None

        return self

    def executemany(self, sql: str, seq_of_parameters):
        translated_sql = self._translate_sql(sql)
        self._cursor.executemany(translated_sql, seq_of_parameters)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return PostgresRow(self._cursor.description, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        desc = self._cursor.description
        return [PostgresRow(desc, r) for r in rows]

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return self

    def __next__(self):
        row = self._cursor.fetchone()
        if row is None:
            raise StopIteration
        return PostgresRow(self._cursor.description, row)


class PostgresConnection:
    """
    Обертка над соединением psycopg2, имитирующая sqlite3.Connection.
    """
    def __init__(self, raw_conn):
        self._conn = raw_conn
        self.row_factory = None

    def cursor(self):
        return PostgresCursor(self._conn.cursor(), self)

    def execute(self, sql: str, parameters=None):
        cur = self.cursor()
        cur.execute(sql, parameters)
        return cur

    def executemany(self, sql: str, seq_of_parameters):
        cur = self.cursor()
        cur.executemany(sql, seq_of_parameters)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_connection():
    """
    Создаёт новое соединение с БД (PostgreSQL или SQLite).
    """
    try:
        import config
        DB_TYPE = getattr(config, "DB_TYPE", "sqlite")
    except ImportError:
        DB_TYPE = "sqlite"

    if DB_TYPE == "postgres":
        try:
            import psycopg2
            raw_conn = psycopg2.connect(
                host=getattr(config, "PG_HOST", "localhost"),
                port=getattr(config, "PG_PORT", 5432),
                database=getattr(config, "PG_DB", "yadreno_vpn"),
                user=getattr(config, "PG_USER", "yadreno_user"),
                password=getattr(config, "PG_PASSWORD", "yadreno_pass"),
                connect_timeout=5
            )
            return PostgresConnection(raw_conn)
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}. Откат на SQLite.")

    # SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    """
    Контекстный менеджер для работы с БД.
    Автоматически делает commit при успехе и rollback при ошибке.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

