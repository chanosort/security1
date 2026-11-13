import psycopg2
import psycopg2.extras
from config import Config
import os

class Database:
    def __init__(self):
        self.config = Config()
        self.connection = None

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                database=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            with self.connection.cursor() as cursor:
                schema = self.config.DB_SCHEMA
                if not schema or not all(c.isalnum() or c == '_' for c in schema):
                    raise ValueError("Invalid DB schema name")
                cursor.execute(f'SET search_path TO "{schema}"')
            print("Connected to PostgreSQL successfully!")
            return self.connection
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def execute_query(self, query, params=None):
        try:
            if not self.connection:
                self.connect()
            if not self.connection:
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
        except Exception as e:
            print(f" Query error: {e}")
            if self.connection:
                self.connection.rollback()
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