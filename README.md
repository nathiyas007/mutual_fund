# Mutual Fund Transaction Dashboard

## Overview

This project is a Mutual Fund Transaction Dashboard built using FastAPI for the backend and HTML, CSS, and JavaScript for the frontend. The application stores transaction data in PostgreSQL and can be connected to a Supabase-hosted PostgreSQL database.

## Project Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Task
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file and add your database connection string:

```env
DATABASE_URL=postgresql://postgres:password@host:5432/database_name
```

### 5. Create Database Tables

Run the setup script:

```bash
python db_setup.py
```

## Running the Application

### Start the Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Backend URL:

```
http://localhost:8000
```

Swagger Documentation:

```
http://localhost:8000/docs
```

### Start the Frontend

```bash
cd frontend
python -m http.server 3000
```

Frontend URL:

```
http://localhost:3000
```

## Available API Endpoints

### Dashboard Metadata

```http
GET /api/dashboard/metadata
```

Returns available investors, schemes, and transaction date range.

### Investor Funds

```http
GET /api/dashboard/investor-funds
```

Returns mutual fund purchase details for a selected investor.

### Fund Investors

```http
GET /api/dashboard/fund-investors
```

Returns investor‑wise details for a selected mutual fund.

### Investors Summary

```http
GET /api/dashboard/investors
```

Returns total investment amount grouped by investor.

### Mutual Funds Summary

```http
GET /api/dashboard/mutual-funds
```

Returns fund‑level metrics such as total investment, units purchased, and average NAV.

## Technology Stack

* Python 3.9+
* FastAPI
* Uvicorn
* PostgreSQL
* Supabase
* psycopg2
* python‑dotenv
* HTML
* CSS
* JavaScript

## Testing the API

You can test all endpoints using:

* Swagger UI (`/docs`)
* Postman
* cURL

## License

This project is licensed under the MIT License.
