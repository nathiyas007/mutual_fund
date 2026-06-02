from fastapi import APIRouter, Query
from database import get_db_connection
from utils import apply_date_filters

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)

@router.get("/metadata")
def get_metadata():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT MIN("traddate"), MAX("traddate") FROM transactions')
            min_date, max_date = cur.fetchone()
            
            cur.execute('SELECT DISTINCT "pan", "inv_name" FROM transactions WHERE "pan" IS NOT NULL ORDER BY "inv_name"')
            investor_rows = cur.fetchall()
            investors = []
            for r in investor_rows:
                investors.append({
                    "pan": r[0].strip() if r[0] else None,
                    "inv_name": r[1].strip() if r[1] else None
                })
                
            cur.execute('SELECT DISTINCT "scheme" FROM transactions WHERE "scheme" IS NOT NULL ORDER BY "scheme"')
            scheme_rows = cur.fetchall()
            schemes = [r[0].strip() for r in scheme_rows]
            
            return {
                "min_date": min_date.strftime("%Y-%m-%d") if min_date else None,
                "max_date": max_date.strftime("%Y-%m-%d") if max_date else None,
                "investors": investors,
                "schemes": schemes
            }

@router.get("/investor-funds")
def get_investor_funds(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    pan: str = Query(None)
):
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

@router.get("/fund-investors")
def get_fund_investors(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    scheme: str = Query(None)
):
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

@router.get("/investors")
def get_investors(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
):
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

@router.get("/mutual-funds")
def get_mutual_funds(
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
):
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

@router.get("/aggregates")
def get_aggregates(
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
    start_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
):
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
