"""
Card components for displaying statistics and plots
"""
from typing import Union

from dash import html, dcc


def create_stat_card(title: str, value: Union[str, int, float], color_class: str = "text-info") -> html.Div:
    """
    Create a statistic card with title and value

    Args:
        title: Display title for the statistic
        value: The value to display (will be converted to string)
        color_class: CSS class for value color (text-info, text-success, text-warning, text-primary)

    Returns:
        html.Div: A styled stat card component
    """
    return html.Div(
        [
            html.Div(title, className="stat-card-title"),
            html.Div(str(value), className=f"stat-card-value {color_class}"),
        ],
        className="stat-card",
    )


def create_plot_card(
    plot_id: str,
    title: str,
    loading_id: Union[str, None] = None,
    loading_color: str = "#17a2b8",
) -> html.Div:
    """
    Create a card container for a plotly graph with loading spinner

    Args:
        plot_id: The ID for the dcc.Graph component
        title: Display title for the plot
        loading_id: Optional custom ID for the loading component
        loading_color: Color for the loading spinner

    Returns:
        html.Div: A card with header and graph area
    """
    if loading_id is None:
        loading_id = f"loading-{plot_id}"

    return html.Div(
        html.Div(
            children=[
                html.Div(
                    [
                        html.H5(
                            title,
                            className="text-blue mb-0",
                        ),
                    ],
                    className="plot-section-header",
                ),
                dcc.Loading(
                    id=loading_id,
                    type="circle",
                    color=loading_color,
                    children=dcc.Graph(id=plot_id),
                ),
            ],
            className="card-body",
        ),
        className="card",
    )
