from pydantic import BaseModel

class Transaction(BaseModel):
    pan: str
    inv_name: str
    scheme: str
    traddate: str  # Expected format YYYY-MM-DD
    amount: float
    units: float
