# Baseball Attendance Analytics Dashboard

## Quick Start

### 1. Ensure Database is Built
From the project root directory:
```bash
source venv/bin/activate
python db_setup.py
```

### 2. Run the Dashboard
```bash
cd frontend
./run.sh
```

Or manually:
```bash
source ../venv/bin/activate
cd src
python app.py
```

### 3. Access the Application
Open your browser to: **http://localhost:8050**

---

## Project Structure

```
frontend/
├── src/
│   ├── app.py              # Main Dash application
│   ├── assets/             # CSS styling
│   │   ├── dashboard.css   # Card, layout, and component styles
│   │   ├── header.css      # Header and navigation styles
│   │   └── typography.css  # Text and color styles
│   ├── components/         # Reusable UI components
│   │   ├── __init__.py
│   │   └── cards.py        # Stat cards and plot cards
│   └── pages/              # Dashboard pages
│       ├── __init__.py
│       └── overview.py     # Overview/Executive Summary page
├── requirements.txt        # Python dependencies
└── run.sh                  # Startup script
```

---

## Current Pages

### Overview (Home)
- **Stat Cards**: Total games, active stadiums, avg attendance, avg runs/game
- **League-Wide Attendance Trend**: Line chart showing attendance from 2000-present
- **Day of Week Analysis**: Bar chart comparing attendance by weekday
- **Day vs Night Comparison**: Dual-axis chart showing attendance and runs

---

## Adding New Pages

1. Create a new file in `src/pages/` (e.g., `team_performance.py`)
2. Import required modules:
   ```python
   import dash
   from dash import html, dcc, callback, Input, Output
   ```
3. Register the page:
   ```python
   dash.register_page(__name__, path="/teams", name="Team Performance", order=2)
   ```
4. Define layout and callbacks
5. The page will automatically appear in navigation

---

## Styling Guidelines

Match the HPC Dashboard aesthetic:
- **Primary accent color**: `#17a2b8` (teal)
- **Success green**: `#28a745`
- **Warning yellow**: `#ffc107`
- **Secondary green**: `#20c997`
- **Background**: `#2d3135`
- **Card background**: `#3e444a`
- **Text**: `#e9ecef`

Use the reusable component functions:
```python
from components import create_stat_card, create_plot_card

# Stat card
create_stat_card("Title", "123,456", "text-info")

# Plot card with loading spinner
create_plot_card("my-graph-id", "Chart Title")
```

---

## Dependencies

- **dash**: Web framework
- **dash-bootstrap-components**: Bootstrap styling for Dash
- **dash-mantine-components**: Additional UI components
- **pandas**: Data manipulation
- **plotly**: Interactive visualizations

---

## Database Connection

Pages import the `AttendanceAnalyzer` class from the parent `queries.py`:
```python
from queries import AttendanceAnalyzer

qa = AttendanceAnalyzer()  # Connects to ../baseball_attendance.db
df = qa.attendance_by_team()
```

---

## Development Tips

- Enable debug mode in `app.py` for hot reloading during development
- Use `print()` statements in callbacks for debugging
- Check browser console for JavaScript errors
- Plotly figures use `plotly_dark` template for consistent theming
