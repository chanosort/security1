import psycopg2
import psycopg2.extras
from config import Config
import os

class Database:
    def __init__(self):
        self.config = Config()
        self.connection = None

    def is_connected(self):
        return self.connection is not None and self.connection.closed == 0

    def connect(self):
        try:
            if self.connection and self.connection.closed == 0:
                try:
                    self.connection.close()
                except Exception:
                    pass
            db_url = os.getenv('DATABASE_URL', '').strip()
            if db_url:
                if db_url.startswith('postgres://'):
                    db_url = db_url.replace('postgres://', 'postgresql://', 1)
                self.connection = psycopg2.connect(
                    db_url,
                    cursor_factory=psycopg2.extras.RealDictCursor,
                    connect_timeout=10
                )
            else:
                self.connection = psycopg2.connect(
                    host=self.config.DB_HOST,
                    port=self.config.DB_PORT,
                    database=self.config.DB_NAME,
                    user=self.config.DB_USER,
                    password=self.config.DB_PASSWORD,
                    cursor_factory=psycopg2.extras.RealDictCursor,
                    connect_timeout=10
                )
            with self.connection.cursor() as cursor:
                schema = self.config.DB_SCHEMA or 'e_tracker'
                if schema and all(c.isalnum() or c == '_' for c in schema):
                    cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                    cursor.execute(f'SET search_path TO "{schema}", public')
            self.connection.commit()
            print("Connected to PostgreSQL successfully!")
            return self.connection
        except Exception as e:
            print(f"Database connection error: {e}")
            self.connection = None
            return None

    def init_db(self):
        try:
            schema_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'DATABASE', 'schema.sql')
            if os.path.exists(schema_file) and self.connect():
                with open(schema_file, 'r', encoding='utf-8') as f:
                    sql = f.read()
                with self.connection.cursor() as cursor:
                    cursor.execute(sql)
                self.connection.commit()
                print("Database tables initialized/verified successfully!")
        except Exception as e:
            print(f"init_db note: {e}")

    def execute_query(self, query, params=None):
        for attempt in range(2):
            try:
                if not self.is_connected():
                    self.connect()
                if not self.is_connected():
                    raise RuntimeError("Database connection unavailable")

                with self.connection.cursor() as cursor:
                    cursor.execute(query, params or ())
                    query_upper = query.strip().upper()

                    # ── ADDED: block any log mutation (Protection 11 / S11) ──
                    if 'ACTIVITY_LOG' in query_upper and (
                        query_upper.startswith('UPDATE') or query_upper.startswith('DELETE')
                    ):
                        raise PermissionError("activity_log is append-only")

                    if query_upper.startswith('SELECT') or 'RETURNING' in query_upper:
                        results = cursor.fetchall()
                        self.connection.commit()
                        return results
                    self.connection.commit()
                    return cursor.rowcount
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"Database connection lost ({e}), attempting reconnect (attempt {attempt+1}/2)...")
                self.connection = None
                if attempt == 1:
                    raise e
            except Exception as e:
                print(f" Query error: {e}")
                if self.is_connected():
                    try:
                        self.connection.rollback()
                    except Exception:
                        pass
                raise e

    def close(self):
        if self.connection:
            self.connection.close()
            print(" Database connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

db = Database()