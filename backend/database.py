import os
from contextlib import contextmanager
from fastapi import HTTPException
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:AcademyRootPassword@localhost:5432/mf_dashboard_db"
)

class Database:
    def __init__(self):
        self.pool = None

    def init_pool(self):
        try:
            self.pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=DATABASE_URL
            )
            print("Database connection pool initialized successfully.")
        except Exception as e:
            print(f"Error initializing database connection pool: {e}")
            raise e

    def close_pool(self):
        if self.pool:
            self.pool.closeall()
            print("Database connection pool closed.")

db = Database()

@contextmanager
def get_db_connection():
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database connection pool is not initialized.")
    conn = db.pool.getconn()
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        db.pool.putconn(conn)
