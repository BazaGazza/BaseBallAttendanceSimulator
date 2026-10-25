"""
Overview Page - Executive Summary Dashboard
Displays high-level metrics and league-wide attendance trends
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import html, callback, Input, Output

# Add parent directories to path to import queries module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from queries import AttendanceAnalyzer
from components import create_stat_card, create_plot_card

dash.register_page(__name__, path="/", name="Overview", order=1)

# Initialize database analyzer
qa = AttendanceAnalyzer()

# Define consistent plot styling to match HPC Dashboard
PLOT_TEMPLATE = "plotly_dark"
PLOT_LAYOUT = {
    "paper_bgcolor": "#2d3135",
    "plot_bgcolor": "#3e444a",
    "font": {"color": "#e9ecef", "family": "Inter, Segoe UI, Roboto, sans-serif"},
    "margin": {"l": 60, "r": 40, "t": 40, "b": 60},
}

# Fetch data for stat cards on page load
try:
    # Get total games count
    games_df = qa._query("SELECT COUNT(*) as total FROM games WHERE gametype = 'regular'")
    total_games = f"{games_df.iloc[0]['total']:,}"

    # Get number of active stadiums
    parks_df = qa._query("SELECT COUNT(DISTINCT park_id) as total FROM games WHERE season >= 2020")
    total_parks = f"{parks_df.iloc[0]['total']}"

    # Get average attendance
    avg_att_df = qa._query(
        "SELECT ROUND(AVG(attendance)) as avg_att FROM games "
        "WHERE gametype = 'regular' AND attendance IS NOT NULL"
    )
    avg_attendance = f"{int(avg_att_df.iloc[0]['avg_att']):,}"

    # Get average runs per game
    avg_runs_df = qa._query(
        "SELECT ROUND(AVG(total_runs), 1) as avg_runs FROM games "
        "WHERE gametype = 'regular' AND total_runs IS NOT NULL"
    )
    avg_runs = f"{avg_runs_df.iloc[0]['avg_runs']}"

except Exception as e:
    print(f"Error loading overview stats: {e}")
    total_games = "N/A"
    total_parks = "N/A"
    avg_attendance = "N/A"
    avg_runs = "N/A"

# Layout
layout = html.Div(
    [
        # Page Title
        html.H1("League Overview", style={"margin": "1rem 0"}),

        # Stat Cards Row
        html.Div(
            [
                create_stat_card("Total Games", total_games, "text-info"),
                create_stat_card("Active Stadiums", total_parks, "text-success"),
                create_stat_card("Avg Attendance", avg_attendance, "text-primary"),
                create_stat_card("Avg Runs/Game", avg_runs, "text-warning"),
            ],
            className="stat-cards-container",
        ),

        # Attendance Trend Chart
        create_plot_card(
            plot_id="attendance-trend-graph",
            title="League-Wide Attendance Trend (2000-Present)",
        ),

        # Day of Week Chart
        create_plot_card(
            plot_id="day-of-week-graph",
            title="Average Attendance by Day of Week",
        ),

        # Day vs Night Chart
        create_plot_card(
            plot_id="day-night-graph",
            title="Day vs Night Game Comparison",
        ),
    ]
)


@callback(
    Output("attendance-trend-graph", "figure"),
    Input("attendance-trend-graph", "id"),
)
def update_attendance_trend(_):
    """Create league-wide attendance trend line chart"""
    try:
        df = qa.attendance_trend()

        # Filter to 2000 and later for cleaner visualization
        df = df[df['season'] >= 2000]

        fig = go.Figure()

        # Add line trace
        fig.add_trace(
            go.Scatter(
                x=df['season'],
                y=df['avg_attendance'],
                mode='lines+markers',
                name='Avg Attendance',
                line=dict(color='#17a2b8', width=3),
                marker=dict(size=8, color='#20c997'),
                hovertemplate='<b>Season: %{x}</b><br>Avg Attendance: %{y:,}<extra></extra>',
            )
        )

        fig.update_layout(
            **PLOT_LAYOUT,
            template=PLOT_TEMPLATE,
            xaxis_title="Season",
            yaxis_title="Average Attendance",
            hovermode="x unified",
            xaxis=dict(
                tickmode='linear',
                tick0=2000,
                dtick=2,
            ),
            yaxis=dict(
                tickformat=',',
            ),
        )

        return fig
    except Exception as e:
        print(f"Error creating attendance trend: {e}")
        return go.Figure()


@callback(
    Output("day-of-week-graph", "figure"),
    Input("day-of-week-graph", "id"),
)
def update_day_of_week(_):
    """Create day of week bar chart"""
    try:
        df = qa.attendance_by_day_of_week()

        # Order days properly
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=day_order, ordered=True)
        df = df.sort_values('day_of_week')

        # Create color scale (weekdays lighter, weekend darker/highlighted)
        colors = ['#3e444a', '#3e444a', '#3e444a', '#3e444a', '#17a2b8', '#20c997', '#28a745']

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=df['day_of_week'],
                y=df['avg_attendance'],
                marker=dict(color=colors, line=dict(color='#17a2b8', width=1)),
                hovertemplate='<b>%{x}</b><br>Avg Attendance: %{y:,}<br>Games: %{customdata:,}<extra></extra>',
                customdata=df['games'],
            )
        )

        fig.update_layout(
            **PLOT_LAYOUT,
            template=PLOT_TEMPLATE,
            xaxis_title="Day of Week",
            yaxis_title="Average Attendance",
            showlegend=False,
            yaxis=dict(tickformat=','),
        )

        return fig
    except Exception as e:
        print(f"Error creating day of week chart: {e}")
        return go.Figure()


@callback(
    Output("day-night-graph", "figure"),
    Input("day-night-graph", "id"),
)
def update_day_night(_):
    """Create day vs night comparison chart"""
    try:
        df = qa.attendance_day_vs_night()

        fig = go.Figure()

        # Attendance bars
        fig.add_trace(
            go.Bar(
                x=df['daynight'],
                y=df['avg_attendance'],
                name='Avg Attendance',
                marker=dict(color='#17a2b8'),
                yaxis='y1',
                hovertemplate='<b>%{x} Games</b><br>Avg Attendance: %{y:,}<extra></extra>',
            )
        )

        # Runs line (secondary axis)
        fig.add_trace(
            go.Scatter(
                x=df['daynight'],
                y=df['avg_runs'],
                name='Avg Runs',
                mode='lines+markers',
                line=dict(color='#ffc107', width=3),
                marker=dict(size=12),
                yaxis='y2',
                hovertemplate='<b>%{x} Games</b><br>Avg Runs: %{y:.1f}<extra></extra>',
            )
        )

        fig.update_layout(
            **PLOT_LAYOUT,
            template=PLOT_TEMPLATE,
            xaxis_title="Game Time",
            yaxis=dict(
                title="Average Attendance",
                side='left',
                tickformat=',',
            ),
            yaxis2=dict(
                title="Average Runs",
                side='right',
                overlaying='y',
                showgrid=False,
            ),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
        )

        return fig
    except Exception as e:
        print(f"Error creating day vs night chart: {e}")
        return go.Figure()
