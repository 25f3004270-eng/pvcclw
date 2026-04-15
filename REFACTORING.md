# PVC Calculator Refactoring Guide

## Overview

This document describes the completed refactoring and remaining steps to fully migrate from the monolithic `app.py` to a modular application structure.

## What Has Been Created

### 1. Application Structure

```
app/
  __init__.py          - Application factory, CSRF, blueprints, CLI
  models.py            - All SQLAlchemy models
  cli.py               - DB initialization command (flask init-db)
  services/
    __init__.py        - GST_FACTOR + rate-applied constants
    helpers.py         - Numeric, date, LD, PVCInput, index helpers
    scenarios.py       - Centralized scenario selection logic
    pvc_ieema.py       - IEEMA PVC percent calculations
    pvc_igbt.py        - IGBT stub (needs P1/P2 vendor logic)
  routes/
    __init__.py        - Routes package marker
    auth.py            - Register, login, logout STUBS
    calculator.py      - Main calculator routes STUBS
    admin.py           - Admin routes STUB
wsgi.py                - WSGI entry point
.env.example           - Environment variables template
requirements.txt       - Updated with Flask-WTF and click
```

### 2. Key Improvements Already Implemented

- **Application factory** in `app/__init__.py` for clean WSGI deployment
- **CSRF protection** via Flask-WTF
- **CLI-based DB initialization** (`flask init-db`) instead of on-import seeding
- **Environment-driven** secret key and admin password
- **Centralized scenario selection** in `app/services/scenarios.py`
- **LRU-cached index loading** in `app/services/helpers.py`
- **Input validation** in `PVCInput.validate()` method
- **Type hints** added to helper functions
- **Rate-applied constants** to avoid typos

---

## NEXT STEPS TO COMPLETE

### Step 1: Copy Route Implementations

The route files are **stubs with TODO comments**. You need to copy the actual route logic from the original `app.py`:

#### `app/routes/auth.py`
- Copy `register()`, `login()` functions from original app.py lines ~690-770
- Change `@app.route` to `@auth_bp.route`
- Change `url_for('login')` to `url_for('auth.login')`

#### `app/routes/calculator.py`
- Copy `index()`, `calculate()`, `history()`, `viewcalc()`, `exportcalcexcel()`, `gettender()` from original app.py lines ~780-900
- Change `@app.route` to `@calc_bp.route`
- **Important:** Update imports:
  - `from ..services.pvc_ieema import calc_single_record`
  - `from ..services.pvc_igbt import calculate_igbt_propulsion`
  - `from ..services.helpers import PVCInput, get_item_index_df`
- Change `url_for('index')` to `url_for('calculator.index')`

#### `app/routes/admin.py`
- Copy all admin routes from original app.py lines ~920-1200
- Change `@app.route` to `@admin_bp.route`
- **Important:** After editing ItemIndex rows, call `invalidate_index_cache()` from `..services.helpers`

### Step 2: Complete IGBT Propulsion Logic

`app/services/pvc_igbt.py` is a **skeleton**. Copy the full implementation from original `app.py` lines ~320-700:

1. `_igbt_index_values(idx_df, month, currency)`
2. `_igbt_p1(indigenous_value, base_idx, curr_idx, weights)`
3. `_igbt_p2(cif_value, base_idx, curr_idx)`
4. `_igbt_vendor_scenario(rate, vendor, base_month, ref_month, idx_df, weights, scenario_label)`
5. The full vendor loop and min-PVC selection logic in `calculate_igbt_propulsion()`

### Step 3: Test Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables (create .env file)
cp .env.example .env
# Edit .env and set SECRET_KEY to a random string

# 3. Initialize database
export FLASK_APP=wsgi:app
flask init-db

# 4. Run locally
python wsgi.py
```

Visit http://localhost:5000 and test:
- Registration and login
- IEEMA calculation (transformer items)
- IGBT calculation (once pvc_igbt.py is completed)
- Admin pages (tenders, vendors, items, indices)

### Step 4: Deploy to Render

Update `Procfile` if needed:
```
web: gunicorn wsgi:app
```

On Render dashboard, set environment variables:
- `SECRET_KEY` (generate a random string)
- `ADMIN_PASSWORD` (choose a strong password)
- `DATABASE_URL` (auto-set by Render MySQL)

After deploy, run the init-db command once via Render shell:
```bash
flask --app wsgi:app init-db
```

### Step 5: Update Procfile

Change `Procfile` from:
```
web: gunicorn app:app
```
to:
```
web: gunicorn wsgi:app
```

---

## Security Checklist

- [ ] Set `SECRET_KEY` from environment (never use fallback in production)
- [ ] Set strong `ADMIN_PASSWORD`
- [ ] CSRF protection enabled (already done via Flask-WTF)
- [ ] Admin actions logged (add `current_app.logger.info` calls)
- [ ] Validate JSON inputs (weights sum to 100, positive indices)

## Performance Checklist

- [ ] Use `joinedload` for N+1 queries in history page (see `app/routes/calculator.py` TODO)
- [ ] Call `invalidate_index_cache()` after ItemIndex edits
- [ ] Consider caching `get_item_index_df` results during request lifecycle

## Code Quality Checklist

- [ ] Add type hints to remaining functions
- [ ] Replace magic strings with constants from `app/services/__init__.py`
- [ ] Add docstrings to complex calculation functions
- [ ] Write unit tests for `pvc_percent`, `calc_ld`, `select_scenario`

---

## File-by-File Completion Status

| File | Status | Action Needed |
|------|--------|---------------|
| `app/__init__.py` | ✅ Complete | None |
| `app/models.py` | ✅ Complete | None |
| `app/cli.py` | ✅ Complete | None |
| `app/services/__init__.py` | ✅ Complete | None |
| `app/services/helpers.py` | ✅ Complete | None |
| `app/services/scenarios.py` | ✅ Complete | None |
| `app/services/pvc_ieema.py` | ✅ Complete | None |
| `app/services/pvc_igbt.py` | ⚠️ Stub | Copy P1/P2 logic from app.py lines 320-700 |
| `app/routes/auth.py` | ⚠️ Stub | Copy register/login routes from app.py |
| `app/routes/calculator.py` | ⚠️ Stub | Copy all calculator routes from app.py |
| `app/routes/admin.py` | ⚠️ Stub | Copy all admin routes from app.py |
| `wsgi.py` | ✅ Complete | None |
| `.env.example` | ✅ Complete | None |
| `requirements.txt` | ✅ Complete | None |

---

## Questions?

If you encounter issues:
1. Check that all imports are correct (use `..` for relative imports within `app/`)
2. Verify `url_for` calls use blueprint prefixes (`auth.login`, `calculator.index`, etc.)
3. Ensure CSRF tokens are in all forms: `{{ csrf_token() }}`
4. Test each route individually before deploying

Good luck with the final migration! 🚀
