import dash
from dash.dependencies import Input, Output, State
from kafka.producer import create_order, send_order
import plotly.graph_objs as go
from backend.order_book import order_book
from frontend.layout import render_table


def register_callbacks(app):
    
    # Callback to update the live order book graph
    @app.callback(
        Output('live-bar-chart', 'figure'),
        [Input('interval-component', 'n_intervals')]
    )
    def update_graph(n):
        stock_symbol = 'AAPL'
        buy_data, sell_data = order_book.sum_quantity_by_price(stock_symbol)

        if not buy_data and not sell_data:
            return go.Figure()  # Return an empty figure if no data is available

        prices = list(set(list(buy_data.keys()) + list(sell_data.keys())))
        prices.sort()

        buy_quantities = [buy_data.get(price, 0) for price in prices]
        sell_quantities = [sell_data.get(price, 0) for price in prices]

        figure = {
            'data': [
                go.Bar(
                    y=prices, x=buy_quantities, name='Buy Orders', orientation='h', marker_color='blue'
                ),
                go.Bar(
                    y=prices, x=sell_quantities, name='Sell Orders', orientation='h', marker_color='red'
                )
            ],
            'layout': go.Layout(
                title=f"Quantity by Price for {stock_symbol}",
                xaxis={'title': 'Quantity'},
                yaxis={'title': 'Price'},
                barmode='overlay',
                hovermode='closest'
            )
        }

        return figure

    # Callback to place an order (buy or sell) and reset the form fields after submission
    @app.callback(
        [Output('price-input', 'value'),
         Output('quantity-input', 'value'),
         Output('user_id-input', 'value'),
         Output('order-feedback', 'children'),
         Output('order-feedback', 'style')],
        [Input('buy-button', 'n_clicks_timestamp'),
         Input('sell-button', 'n_clicks_timestamp')],
        [State('price-input', 'value'),
         State('quantity-input', 'value'),
         State('user_id-input', 'value')]
    )
    def place_order(buy_click_timestamp, sell_click_timestamp, price, quantity, user_id):
        if price is None or quantity is None or user_id is None:
            return dash.no_update, dash.no_update, dash.no_update, "", dash.no_update  # No update if inputs are not provided

        stock_symbol = 'AAPL'
        feedback_message = ""
        feedback_style = {}

        # Check which button was clicked last using timestamps
        if buy_click_timestamp is not None and (sell_click_timestamp is None or buy_click_timestamp > sell_click_timestamp):
            # Create a buy order to send to Kafka
            order = create_order(user_id=user_id, order_type='buy', stock_id=stock_symbol, price=price, quantity=quantity)
            send_order(order)  # Send the order to Kafka
            feedback_message = f"Buy order placed: {quantity} @ {price}"
            feedback_style = {'color': 'green'}
            print(f"Sent buy order: {quantity} @ {price}")
        elif sell_click_timestamp is not None and (buy_click_timestamp is None or sell_click_timestamp > buy_click_timestamp):
            # Create a sell order to send to Kafka
            order = create_order(user_id=user_id, order_type='sell', stock_id=stock_symbol, price=price, quantity=quantity)
            send_order(order)  # Send the order to Kafka
            feedback_message = f"Sell order placed: {quantity} @ {price}"
            feedback_style = {'color': 'lightcoral'}
            print(f"Sent sell order: {quantity} @ {price}")

        # Reset the input fields after placing the order
        return "", 100, "", feedback_message, feedback_style


    # Callback to update buy and sell queues in the UI
    @app.callback(
        Output('order-queue', 'children'),  # Update the children property of the table body
        [Input('interval-component', 'n_intervals')]
    )
    def update_queues(n):
        order_rows = order_book.get_order_rows()  # Fetch rows directly from OrderBook
        return render_table(order_rows)