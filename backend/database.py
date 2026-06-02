import os
from psycopg2 import pool
from contextlib import contextmanager
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:AcademyRootPassword@localhost:5432/mf_dashboard_db"
)

db_pool = None

def init_db_pool():
    global db_pool
    db_pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        dsn=DATABASE_URL
    )
    return db_pool

def close_db_pool():
    global db_pool
    if db_pool:
        db_pool.closeall()

@contextmanager
def get_db_connection():
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database connection pool is not initialized.")
    conn = db_pool.getconn()
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        db_pool.putconn(conn)
