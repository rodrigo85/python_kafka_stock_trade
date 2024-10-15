from dash import Dash
from frontend.layout import create_layout
from frontend.callbacks import register_callbacks

# Initialize the Dash app
app = Dash(__name__)

# Set the layout
app.layout = create_layout()

# Register the callbacks
register_callbacks(app)

if __name__ == '__main__':
    app.run_server(debug=True)
