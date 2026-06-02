from contextlib import asynccontextmanager, contextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import pool
import os
import datetime

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Transaction(BaseModel):
    pan: str
    inv_name: str
    scheme: str
    traddate: str  # Expected format YYYY-MM-DD
    amount: float
    units: float

# DB connection config
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:AcademyRootPassword@localhost:5432/mf_dashboard_db"
)

db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the lifespan of the FastAPI application.
    Initializes and cleans up the PostgreSQL connection pool.
    """
    global db_pool
    try:
        db_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=DATABASE_URL
        )
        print("Database connection pool initialized successfully.")
    except Exception as e:
        print(f"Error initializing database connection pool: {e}")
        raise e
    yield
    if db_pool:
        db_pool.closeall()
        print("Database connection pool closed.")

# Create FastAPI app
app = FastAPI(
    title="Mutual Fund Transaction Dashboard API",
    description="Backend API services for mutual fund analytics and metrics reporting.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Mutual Fund Transaction Dashboard API",
        "docs": "/docs"
    }

@contextmanager
def get_db_connection():
    """
    Context manager to safely get and return a connection from the pool.
    """
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

def apply_date_filters(query, params, start_date, end_date):
    """
    Appends start_date and end_date filters to the query.
    Appends ' 23:59:59' to end_date to ensure inclusive day matching.
    """
    if start_date:
        query += ' AND "traddate" >= %s'
        params.append(start_date)
    if end_date:
        query += ' AND "traddate" <= %s'
        params.append(f"{end_date} 23:59:59")
    return query, params

@app.get("/api/dashboard/metadata")
def get_metadata():
    """
    Helper route to fetch date bounds, unique schemes, and unique investors 
    for UI filtering controls and defaults.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Query Min and Max Date
            cur.execute('SELECT MIN("traddate"), MAX("traddate") FROM transactions')
            min_date, max_date = cur.fetchone()
            
            # Query unique list of investors (PAN and Name)
            cur.execute('SELECT DISTINCT "pan", "inv_name" FROM transactions WHERE "pan" IS NOT NULL ORDER BY "inv_name"')
            investor_rows = cur.fetchall()
            investors = []
            for r in investor_rows:
                investors.append({
                    "pan": r[0].strip() if r[0] else None,
                    "inv_name": r[1].strip() if r[1] else None
                })
                
            # Query unique list of schemes
            cur.execute('SELECT DISTINCT "scheme" FROM transactions WHERE "scheme" IS NOT NULL ORDER BY "scheme"')
            scheme_rows = cur.fetchall()
            schemes = [r[0].strip() for r in scheme_rows]
            
            return {
                "min_date": min_date.strftime("%Y-%m-%d") if min_date else None,
                "max_date": max_date.strftime("%Y-%m-%d") if max_date else None,
                "investors": investors,
                "schemes": schemes
            }

@app.get("/api/dashboard/investor-funds")
def get_investor_funds(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    pan: str = Query(None)
):
    """
    1. Investor-wise Purchase Summary per Mutual Fund.
    Shows total amount and total units purchased grouped by mutual fund for a selected investor or overall.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT 
                    "scheme",
                    SUM("amount") as total_amount,
                    SUM("units") as total_units
                FROM transactions
                WHERE 1=1
            """
            params = []
            query, params = apply_date_filters(query, params, start_date, end_date)
            if pan:
                query += ' AND "pan" = %s'
                params.append(pan)
            query += ' GROUP BY "scheme" ORDER BY total_amount DESC'
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "scheme": row[0].strip() if row[0] else "Unknown Scheme",
                    "total_amount": float(row[1]) if row[1] is not None else 0.0,
                    "total_units": float(row[2]) if row[2] is not None else 0.0
                })
            return results

@app.get("/api/dashboard/fund-investors")
def get_fund_investors(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    scheme: str = Query(None)
):
    """
    2. Mutual Fund-wise Summary per Investor.
    Shows a structured breakdown of each mutual fund and the individual investors who bought it.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT 
                    "scheme",
                    "pan",
                    "inv_name",
                    SUM("amount") as total_amount,
                    SUM("units") as total_units
                FROM transactions
                WHERE 1=1
            """
            params = []
            query, params = apply_date_filters(query, params, start_date, end_date)
            if scheme:
                query += ' AND "scheme" = %s'
                params.append(scheme)
            query += ' GROUP BY "scheme", "pan", "inv_name" ORDER BY "scheme" ASC, total_amount DESC'
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "scheme": row[0].strip() if row[0] else "Unknown Scheme",
                    "pan": row[1].strip() if row[1] else "Unknown PAN",
                    "inv_name": row[2].strip() if row[2] else "Unknown Investor",
                    "total_amount": float(row[3]) if row[3] is not None else 0.0,
                    "total_units": float(row[4]) if row[4] is not None else 0.0
                })
            return results

@app.get("/api/dashboard/investors")
def get_investors(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    3. Investor List with Purchase Details.
    Shows Investor PAN number, name, and total amount invested.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT 
                    "pan",
                    MAX("inv_name") as inv_name,
                    SUM("amount") as total_amount
                FROM transactions
                WHERE 1=1
            """
            params = []
            query, params = apply_date_filters(query, params, start_date, end_date)
            query += ' GROUP BY "pan" ORDER BY total_amount DESC'
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "pan": row[0].strip() if row[0] else "Unknown PAN",
                    "inv_name": row[1].strip() if row[1] else "Unknown Investor",
                    "total_amount": float(row[2]) if row[2] is not None else 0.0
                })
            return results

@app.get("/api/dashboard/mutual-funds")
def get_mutual_funds(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    4. Mutual Fund Summary.
    High-level metric tracking per mutual fund, showing Total Amount, Total Units, and Average NAV Price.
    Average NAV Price = sum(Amount) / sum(Units).
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT 
                    "scheme",
                    SUM("amount") as total_amount,
                    SUM("units") as total_units,
                    CASE 
                        WHEN SUM("units") > 0 THEN SUM("amount") / SUM("units")
                        ELSE 0 
                    END as avg_nav
                FROM transactions
                WHERE 1=1
            """
            params = []
            query, params = apply_date_filters(query, params, start_date, end_date)
            query += ' GROUP BY "scheme" ORDER BY total_amount DESC'
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "scheme": row[0].strip() if row[0] else "Unknown Scheme",
                    "total_amount": float(row[1]) if row[1] is not None else 0.0,
                    "total_units": float(row[2]) if row[2] is not None else 0.0,
                    "avg_nav": float(row[3]) if row[3] is not None else 0.0
                })
            return results

def parse_date(date_str: str):
    """
    Parse date strings into datetime objects.
    Supports formats like '31/05/2026', '2026-05-31', '5/27/2025 12:00:00 AM', etc.
    """
    if not date_str or date_str.strip() == '':
        return None
    date_str = date_str.strip().strip("'")
    formats = [
        '%d/%m/%Y',              # 31/05/2026
        '%m/%d/%Y %I:%M:%S %p',  # 5/27/2025 12:00:00 AM
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',              # 2026-05-31
        '%m/%d/%Y',
        '%d-%m-%Y',
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

@app.post("/api/transactions")
def create_transaction(tx: Transaction):
    """
    Create a new transaction record.
    """
    parsed_date = parse_date(tx.traddate)
    if parsed_date is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: '{tx.traddate}'. Use DD/MM/YYYY or YYYY-MM-DD."
        )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO transactions (pan, inv_name, scheme, traddate, amount, units)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (tx.pan, tx.inv_name, tx.scheme, parsed_date, tx.amount, tx.units)
            )
            conn.commit()
    return {"status": "success", "message": "Transaction created"}

@app.get("/api/dashboard/aggregates")
def get_aggregates(
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Aggregated total amount and units per scheme based on the selected period.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = '''
                SELECT
                    date_trunc(%s, traddate) AS period_start,
                    scheme,
                    SUM(amount) AS total_amount,
                    SUM(units) AS total_units
                FROM transactions
                WHERE 1=1
                '''
            params = []
            query, params = apply_date_filters(query, params, start_date, end_date)
            query += ' GROUP BY period_start, scheme ORDER BY period_start, total_amount DESC'
            cur.execute(query, (period,) + tuple(params))
            rows = cur.fetchall()
            results = []
            for row in rows:
                results.append({
                    "period_start": row[0].strftime("%Y-%m-%d") if row[0] else None,
                    "scheme": row[1].strip() if row[1] else "Unknown Scheme",
                    "total_amount": float(row[2]) if row[2] is not None else 0.0,
                    "total_units": float(row[3]) if row[3] is not None else 0.0
                })
            return results
