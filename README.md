# Jiseti Backend

Flask + PostgreSQL REST API for Jiseti.

## Included
- Register/login with JWT
- Red-Flag and Intervention CRUD
- DRAFT-only edit/delete/location changes
- Area name + latitude/longitude storage
- Admin status changes and status history
- Public community reports endpoint
- PostgreSQL support

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Health: `GET /api/health`
Public reports: `GET /api/public/reports`
