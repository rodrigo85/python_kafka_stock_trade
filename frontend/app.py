"""Dash web application for the real-time stock trading order book."""

import os
from dash import Dash
from frontend.callbacks import register_callbacks
from frontend.layout import create_layout

# Initialize the Dash application with modern styling
app = Dash(__name__, title="Real-Time Order Matching Engine", update_title=None)

# Set the layout
app.layout = create_layout()

# Register event callbacks
register_callbacks(app)

if __name__ == "__main__":
    host = os.getenv("DASH_HOST", "0.0.0.0")
    port = int(os.getenv("DASH_PORT", 8050))
    debug = os.getenv("DASH_DEBUG", "false").lower() in ("true", "1")
    app.run(host=host, port=port, debug=debug)
