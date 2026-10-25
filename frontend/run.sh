#!/bin/bash
# Startup script for Baseball Attendance Dashboard

# Activate virtual environment
source ../venv/bin/activate

# Run the Dash application
cd src
python app.py
