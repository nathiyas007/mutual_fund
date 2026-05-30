import csv
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Connection Details
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:AcademyRootPassword@localhost:5432/mf_dashboard_db"
)

def get_pg_connection():
    """
    Establish a connection to the PostgreSQL server using DATABASE_URL.
    """
    return psycopg2.connect(DATABASE_URL)

def create_database():
    """
    Skipping database creation for Supabase PostgreSQL.
    """
    print("Skipping database creation. Connecting directly to the Supabase database...")


def parse_date(date_str):
    """
    Parse date strings safely into datetime objects.
    Handles '5/27/2025 12:00:00 AM' and other common formats.
    """
    if not date_str or date_str.strip() == '' or date_str.strip().lower() == 'null':
        return None
    date_str = date_str.strip().strip("'")
    
    # Try different format mappings
    formats = [
        '%m/%d/%Y %I:%M:%S %p',  # e.g., '5/27/2025 12:00:00 AM'
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%d/%m/%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    print(f"Warning: Could not parse date string '{date_str}'")
    return None

def parse_float(val):
    """
    Safely convert strings to float.
    """
    if not val or val.strip() == '' or val.strip().lower() == 'null':
        return None
    val = val.strip().strip("'").replace(',', '')
    try:
        return float(val)
    except ValueError:
        return None

def parse_int(val):
    """
    Safely convert strings to integer.
    """
    if not val or val.strip() == '' or val.strip().lower() == 'null':
        return None
    val = val.strip().strip("'").replace(',', '')
    try:
        return int(float(val))  # Convert to float first to handle '123.0'
    except ValueError:
        return None

def setup_db_and_ingest():
    """
    Performs full setup:
    1. Recreates database.
    2. Drops and creates table based on CSV structure.
    3. Reads, parses, cleans, and batch inserts CSV rows.
    """
    create_database()
    
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    csv_file_path = os.path.join(os.path.dirname(__file__), 'dataset.csv')
    
    if not os.path.exists(csv_file_path):
        print(f"Error: Dataset not found at {csv_file_path}")
        return

    print(f"Reading headers from {csv_file_path}...")
    with open(csv_file_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f, quotechar="'")
        headers = next(reader)
        
    # Standardize column headers
    headers = [h.strip().lower() for h in headers]
    
    # Define mapping of columns that need to be numeric or dates
    col_types = {
        'traddate': 'TIMESTAMP',
        'postdate': 'TIMESTAMP',
        'purprice': 'NUMERIC(18, 4)',
        'units': 'NUMERIC(18, 4)',
        'amount': 'NUMERIC(18, 4)',
        'tax': 'NUMERIC(18, 4)',
        'total_tax': 'NUMERIC(18, 4)',
        'brokperc': 'NUMERIC(10, 4)',
        'brokcomm': 'NUMERIC(18, 4)',
        'stt': 'NUMERIC(18, 4)',
        'trxn_charges': 'NUMERIC(18, 4)',
        'eligib_amt': 'NUMERIC(18, 4)',
        'igst_amount': 'NUMERIC(18, 4)',
        'cgst_amount': 'NUMERIC(18, 4)',
        'sgst_amount': 'NUMERIC(18, 4)',
        'stamp_duty': 'NUMERIC(18, 4)',
        'trxnno': 'BIGINT',
        'usrtrxno': 'BIGINT',
        'seq_no': 'BIGINT',
        'sys_regn_date': 'TIMESTAMP',
        'ca_initiated_date': 'TIMESTAMP',
        'rep_date': 'TIMESTAMP',
        'ticob_posted_date': 'TIMESTAMP',
    }
    
    # Build column schema
    create_cols = []
    for h in headers:
        sql_type = col_types.get(h, 'TEXT')
        create_cols.append(f'"{h}" {sql_type}')
        
    create_table_sql = f'DROP TABLE IF EXISTS transactions; CREATE TABLE transactions (id SERIAL PRIMARY KEY, {", ".join(create_cols)});'
    
    print("Recreating 'transactions' table...")
    cursor.execute(create_table_sql)
    conn.commit()
    
    print("Ingesting data...")
    batch_size = 500
    batch = []
    
    with open(csv_file_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f, quotechar="'")
        next(reader)  # Skip header
        
        for row in reader:
            if not row or not any(row):
                continue
                
            # Align row lengths in case of parsing discrepancies
            if len(row) < len(headers):
                row = row + [''] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]
                
            parsed_row = []
            for h, val in zip(headers, row):
                val_stripped = val.strip()
                sql_type = col_types.get(h, 'TEXT')
                
                if sql_type == 'TIMESTAMP':
                    parsed_row.append(parse_date(val_stripped))
                elif sql_type.startswith('NUMERIC'):
                    parsed_row.append(parse_float(val_stripped))
                elif sql_type == 'BIGINT':
                    parsed_row.append(parse_int(val_stripped))
                else:
                    parsed_row.append(val_stripped)
                    
            batch.append(tuple(parsed_row))
            
            if len(batch) >= batch_size:
                insert_batch(cursor, headers, batch)
                batch = []
                
        if batch:
            insert_batch(cursor, headers, batch)
            
    conn.commit()
    print("Data ingestion completed successfully!")
    
    # Verify count
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0]
    print(f"Total transactions stored: {count}")
    
    cursor.close()
    conn.close()

def insert_batch(cursor, headers, batch):
    """
    Executes a batch insert into the transactions table.
    """
    col_names = ", ".join([f'"{h}"' for h in headers])
    placeholders = ", ".join(["%s"] * len(headers))
    sql = f'INSERT INTO transactions ({col_names}) VALUES ({placeholders})'
    cursor.executemany(sql, batch)

if __name__ == '__main__':
    setup_db_and_ingest()
