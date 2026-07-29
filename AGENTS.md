# Wealth VN — Project Guide

## Overview
Vietnamese personal wealth management app (stocks, gold, FX, income tracking).

## Stack
- **Backend**: FastAPI + SQLModel + SQLite (WAL) + APScheduler + sqlite-vec
- **Frontend**: React 18 + Vite 8 + TanStack Query 5 + Tailwind + Recharts
- **AI**: Gemini (primary) + Ollama (fallback) for news tagging
- **Launcher**: PowerShell (start.ps1) auto-installs Python 3.13 + Node 22

## Commands
### Backend
```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v          # run tests
python -m pytest tests/ --cov=.     # run with coverage
python main.py                      # start dev server (port 8000)
alembic revision --autogenerate -m "description"  # create migration
alembic upgrade head                # apply migrations
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # dev server (port 5173)
npm run build        # production build (tsc + vite build)
npx tsc --noEmit     # type check only
```

### Full app
Run `start.bat` or `start.ps1` in the project root.

## Project Structure
- `backend/` — FastAPI backend
  - `api/` — route modules
  - `services/` — business logic
  - `models.py` — SQLModel tables
  - `schemas.py` — Pydantic schemas
  - `database.py` — DB engine + migrations
  - `alembic/` — Alembic migrations
  - `jobs/` — scheduled tasks
  - `tests/` — pytest tests
- `frontend/` — React frontend
  - `src/pages/` — route pages
  - `src/components/` — UI components
  - `src/api/` — API client functions
  - `src/lib/` — utilities
  - `src/stores/` — Zustand stores
  - `src/i18n/` — Vietnamese translations
- `src-tauri/` — Tauri desktop wrapper (scaffold)
- `start.ps1` — Windows launcher

## Conventions
- Backend: use logging module (not print), follow existing SQLModel patterns
- Frontend: use TanStack Query for server state, Zustand for UI state
- All UI text in Vietnamese
- Use Intl.NumberFormat('vi-VN') for number/currency formatting
