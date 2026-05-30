# Mutual Fund Transaction Dashboard

## Live Application

https://mutual-fund-sigma.vercel.app/

## Overview

This project is a Mutual Fund Transaction Dashboard built using FastAPI for the backend and HTML, CSS, and JavaScript for the frontend. The application stores transaction data in PostgreSQL and can be connected to a Supabase-hosted PostgreSQL database.

## Project Setup

### 1. Create and Activate Virtual Environment

```cmd
python -m venv venv
```

Activate the virtual environment:

```cmd
venv\Scripts\activate
```

### 2. Install Dependencies

```cmd
pip install -r backend\requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file and add your database connection string:

```env
DATABASE_URL=postgresql://postgres:password@host:5432/database_name
```

### 4. Create Database Tables

Run the setup script:

```cmd
python db_setup.py
```

---

## Running the Application

### Start the Backend

```cmd
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

```cmd
cd frontend
python -m http.server 3000
```

Frontend URL:

```
http://localhost:3000
```

---

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

Returns investor-wise details for a selected mutual fund.

### Investors Summary

```http
GET /api/dashboard/investors
```

Returns total investment amount grouped by investor.

### Mutual Funds Summary

```http
GET /api/dashboard/mutual-funds
```

Returns fund-level metrics such as total investment, units purchased, and average NAV.

---

## Deployment

- Vercel

---

## Technology Stack

- Python 3.9+
- FastAPI
- Uvicorn
- PostgreSQL
- Supabase
- psycopg2
- python-dotenv
- HTML
- CSS
- JavaScript

---

## UI Design

- UI Output: https://drive.google.com/file/d/19tqEsrroGXRECI1S6ktf5RVa_4iWi2kO/view?usp=sharing

## Endpoint Overview

- Endpoints: https://drive.google.com/file/d/1MSthLwzeWZGU-PwbhdNPV0kbveE0BHgo/view?usp=sharing

---

## Testing the API

You can test all endpoints using:

- Swagger UI (`/docs`)