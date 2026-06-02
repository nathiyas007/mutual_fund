import datetime

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

def parse_date(date_str: str):
    """
    Parse date strings into datetime objects.
    Supports formats like '31/05/2026', '2026-05-31', '5/27/2025 12:00:00 AM', etc.
    """
    if not date_str or date_str.strip() == '':
        return None
    date_str = date_str.strip().strip("'")
    formats = [
        '%d/%m/%Y',
        '%m/%d/%Y %I:%M:%S %p',
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d-%m-%Y',
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None
