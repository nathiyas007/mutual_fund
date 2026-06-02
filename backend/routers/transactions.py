from fastapi import APIRouter, HTTPException
from database import get_db_connection
from schemas import Transaction
from utils import parse_date

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"]
)

@router.post("/")
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
