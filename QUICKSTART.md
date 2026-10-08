# Baseball Attendance Dashboard - Quick Start Guide

## 🚀 Run the Dashboard (TL;DR)

```bash
cd frontend && ./run.sh
```

Then open: **http://localhost:8050**

---

## First Time Setup

### 1. Build the Database (One Time)
```bash
source venv/bin/activate
python db_setup.py
```

This creates `baseball_attendance.db` with 84K+ games from your CSV files.

### 2. Test Everything Works
```bash
source venv/bin/activate
python test_plots.py
```

You should see ✅ for all tests.

### 3. Launch Dashboard
```bash
cd frontend
./run.sh
```

---

## What You'll See

### Overview Page
- **4 stat cards** at the top showing key metrics
- **Attendance trend** line chart (2000-present)
- **Day of week** bar chart showing Saturday/Sunday peaks
- **Day vs night** comparison with dual axes

### Navigation
- Click nav links at the top to switch pages
- Active page is highlighted in teal

### Interactivity
- Hover over charts for detailed tooltips
- Zoom/pan on plots using Plotly toolbar
- Loading spinners while data fetches

---

## Project Layout

```
BaseBallAttendanceSimulator/
├── clean_*.csv              # Raw data files
├── db_setup.py              # Database builder
├── queries.py               # SQL query functions
├── baseball_attendance.db   # SQLite database (generated)
├── test_plots.py            # Validation script
└── frontend/
    ├── run.sh               # Startup script
    └── src/
        ├── app.py           # Main Dash app
        ├── assets/          # CSS files
        ├── components/      # Reusable UI components
        └── pages/           # Dashboard pages
```

---

## Common Commands

### Run the dashboard
```bash
cd frontend && ./run.sh
```

### Rebuild database (force)
```bash
source venv/bin/activate
python db_setup.py --force
```

### Test queries
```bash
source venv/bin/activate
python queries.py
```

### Run validation
```bash
source venv/bin/activate
python test_plots.py
```

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'dash'"**
- Install frontend dependencies: `cd frontend && pip install -r requirements.txt`

**"Database not found"**
- Run `python db_setup.py` from project root

**Dashboard won't start**
- Check you're in frontend/ directory when running `./run.sh`
- Ensure venv is activated: `source ../venv/bin/activate`

**Plots not showing**
- Check browser console (F12) for errors
- Check terminal for Python errors
- Verify database has data: `sqlite3 baseball_attendance.db "SELECT COUNT(*) FROM games;"`

---

## Next Steps

1. **Add more pages** - See `frontend/README.md` for how to add Team Performance, Weather Impact, etc.
2. **Customize styling** - Edit CSS in `frontend/src/assets/`
3. **Add filters** - Use Dash dropdowns and date pickers for interactivity
4. **Deploy** - Use Gunicorn + Nginx, or host on Render/Heroku/PythonAnywhere

---

## Need Help?

- **Frontend documentation**: `frontend/README.md`
- **Full setup details**: `DASHBOARD_SETUP.md`
- **Data dictionary**: `DATA_GUIDE.md`
- **Query examples**: Run `python queries.py`

Built with ❤️ using Python Dash, matching your HPC Dashboard design system.
