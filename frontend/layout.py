from dash import dcc, html

# Function to render table rows from the order data
def render_table(order_rows):
    table_rows = []
    for row in order_rows:
        table_rows.append(html.Tr([
            html.Td(row['buy_qty'], style={'textAlign': 'center'}),
            html.Td(row['price'], style={'textAlign': 'center'}),
            html.Td(row['sell_qty'], style={'textAlign': 'center'})
        ]))
    return table_rows

def create_layout():
    return html.Div([   
        # Graph to display the order book
        dcc.Graph(id='live-bar-chart', style={'margin-bottom': '20px'}),
        
        # Order Queue (Buy, Price, Sell) - using html.Table for alignment
        html.Div([
            html.Table([
                # Table Header
                html.Tr([
                    html.Th('Buy Quantity', style={'width': '33%', 'textAlign': 'center'}),
                    html.Th('Price', style={'width': '33%', 'textAlign': 'center'}),
                    html.Th('Sell Quantity', style={'width': '33%', 'textAlign': 'center'}),
                ]),
                # Table Body - to be populated by data from the callback
                html.Tbody(id='order-queue', children=render_table([]))
            ], style={'width': '100%', 'margin': '0 auto', 'border': '1px solid #ccc'})
        ], style={'padding': '10px', 'border': '1px solid #ccc', 'margin-bottom': '20px'}),

        # Inputs for placing an order
        html.Div([
            # Price Input
            html.Div([
                html.Label('Price:', style={'display': 'block', 'font-weight': 'bold', 'margin-bottom': '5px'}),
                dcc.Input(
                    id='price-input',
                    type='number',
                    placeholder='Enter price',
                    min=0, 
                    style={'width': '100%', 'padding': '10px', 'border': '2px solid #ccc', 'border-radius': '5px', 'font-size': '16px'}
                ),
            ], style={'margin-bottom': '20px'}),

            # Quantity Dropdown
            html.Div([
                html.Label('Quantity:', style={'display': 'block', 'font-weight': 'bold', 'margin-bottom': '5px'}),
                dcc.Dropdown(
                    id='quantity-input',
                    options=[{'label': str(i), 'value': i} for i in range(100, 600, 100)],
                    value=100,
                    style={'width': '100%', 'padding': '10px'}
                ),
            ], style={'margin-bottom': '20px'}),

            # User ID Input
            html.Div([
                html.Label('User ID:', style={'display': 'block', 'font-weight': 'bold', 'margin-bottom': '5px'}),
                dcc.Input(id='user_id-input', type='text', placeholder='Enter User ID', style={'width': '100%', 'padding': '10px', 'border-radius': '5px'}),
            ], style={'margin-bottom': '20px'}),
        ], style={'width': '300px', 'margin': '0 auto'}),

        # Buy and Sell Buttons
        html.Div([
            html.Button('Place Buy Order', id='buy-button', n_clicks=0, 
                        style={'background-color': 'green', 'color': 'white', 'padding': '10px 20px', 'width': '100%', 'margin-bottom': '10px'}),
            html.Button('Place Sell Order', id='sell-button', n_clicks=0, 
                        style={'background-color': 'lightcoral', 'color': 'white', 'padding': '10px 20px', 'width': '100%'}),
        ], style={'width': '300px', 'margin': '0 auto'}),
       
        # User feedback message
        html.Div(id='order-feedback', style={'color': 'green', 'font-size': '16px', 'margin-top': '20px', 'text-align': 'center'}),

        # Interval for refreshing the graph
        dcc.Interval(
            id='interval-component',
            interval=2 * 1000,  # Update every 2 seconds
            n_intervals=0
        )
    ], style={'padding': '20px'})
