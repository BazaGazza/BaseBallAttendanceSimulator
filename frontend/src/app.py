"""
Baseball Attendance Analytics Dashboard
Main application file with multi-page navigation
"""

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import Dash, html, dcc, callback, Input, Output

__version__ = "1.0.0"

app = Dash(
    use_pages=True,
    title="Baseball Attendance Analytics",
    external_stylesheets=[dbc.themes.SLATE],
)

app.layout = dmc.MantineProvider(
    forceColorScheme="dark",
    children=[
        html.Div(
            [
                # Header
                html.Div(
                    className="app-header",
                    children=[
                        html.H1(
                            "Baseball Attendance Analytics",
                            className="app-header--title",
                        ),
                    ],
                ),
                # Navigation Links
                dcc.Location(id="url", refresh=False),
                html.Nav(
                    id="nav-container",
                    className="nav-links",
                ),
                # Page Content
                html.Div(id="page-content", children=[dash.page_container]),
            ]
        )
    ],
)

# Expose server for production deployment
server = app.server


@callback(
    Output("nav-container", "children"),
    Input("url", "pathname"),
)
def update_active_nav(pathname):
    """Update navigation to show active page"""
    if pathname is None:
        pathname = "/"

    nav_links = []

    # Sort pages by order parameter
    sorted_pages = sorted(
        dash.page_registry.values(), key=lambda p: p.get("order", 999)
    )

    for page in sorted_pages:
        # Determine if this is the active page
        is_active = pathname == page["relative_path"]

        # Add 'nav-link--selected' class if active
        class_name = "nav-link nav-link--selected" if is_active else "nav-link"

        nav_links.append(
            dcc.Link(
                page["name"],
                href=page["relative_path"],
                className=class_name,
                id={"type": "nav-link", "page": page["relative_path"]},
            )
        )

    return nav_links


if __name__ == "__main__":
    app.run(debug=False, port="8050")
