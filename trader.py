from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string
import jsonpickle
      
POSITION_VOLUME_LIMIT = 50
AVERAGE_WINDOW_SIZE = 100
DISCOUNT_FACTOR = 0.9
BUY_PRICE_MARGIN = 1
SELL_PRICE_MARGIN = 1
TRADE_VOLUME = 1

class Average:
    def __init__(self, window_size: int = AVERAGE_WINDOW_SIZE):
        self.samples = 0
        self.average_price = 0
        self.prices_window = [] 
        self.window_size = window_size
        
    def update(self, price):
        if (len(self.prices_window) == self.window_size):
            last  = self.prices_window.pop(0)
            self.average_price = self.average_price - (last + price) / self.window_size
        else:
            self.average_price = (self.average_price * len(self.prices_window) + price) / (len(self.prices_window) + 1)
        self.prices_window.append(price)
        self.samples += 1

    def is_good_approximation(self):
        return self.samples >= self.window_size

class TraderPosition:
    def __init__(self):
        self.avg_price = 0
        self.volume = 0

    def check_trade_allowed(self, volume):
        return abs(self.volume + volume) <= POSITION_VOLUME_LIMIT
    
    def update(self, price, volume):
        new_volume = volume + self.volume
        if new_volume != 0:
            self.avg_price = (price * volume + self.avg_price * self.volume) / new_volume
        self.volume = new_volume

class ProductData:
    def __init__(self):
        self.average : Average = Average()
        self.position : TraderPosition = TraderPosition()
        self.iteration : int = 1

    def update(self, trade_prices, new_orders):
        self.iteration += 1
        for trade_price in trade_prices:
            self.average.update(trade_price)
        for order in new_orders:
            self.position.update(order.price, order.quantity)

class CurrentMarketProductData:
    def __init__(self):
        self.sell_orders : List[tuple[int, int]] = []
        self.buy_orders : List[tuple[int, int]] = []
        self.sell_average : Average = Average()
        self.buy_average : Average = Average()


class TraderData:
    def __init__(self):
        self.products : dict[str, ProductData] = {}

class Trader:
    """
    TODO:
    - When selling or buying we should take into account the other side also
    - We can also add propotionality to the volume we want to trade depending on how big is the spred between average and current
    """
    def run(self, state: TradingState):
        traderData = self.load_trader_data(state)
        processed_market_orders = self.process_market_orders(traderData.products, state.order_depths)
        own_trades = self.apply_per_trading_strategy(traderData.products, processed_market_orders)
        return own_trades, 1, jsonpickle.encode(traderData)

    def process_market_orders(self, trader_product_data: dict[str, ProductData], current_market: dict[str, OrderDepth]): 
        processed_market_orders = {}
        for product in current_market.keys():
            order_depth: OrderDepth = current_market[product]
            if product not in trader_product_data:
                trader_product_data[product] = ProductData()
            product_data: ProductData = trader_product_data[product]

            current_product_data = CurrentMarketProductData()
            current_product_data.sell_orders = sorted(list(order_depth.sell_orders.items()), key=lambda x: (x[0], abs(x[1])))
            current_product_data.buy_orders = sorted(list(order_depth.buy_orders.items()), key=lambda x: (-x[0], abs(x[1])))

            for order in order_depth.sell_orders.items():
                current_product_data.sell_average.update(order[0])
                product_data.average.update(order[0])
            for order in order_depth.buy_orders.items():
                current_product_data.buy_average.update(order[0])
                product_data.average.update(order[0])
            processed_market_orders[product] = current_product_data

        return processed_market_orders
            

    def load_trader_data(self, state):
        if not state.traderData:
            traderData = TraderData()
        else:
            traderData = jsonpickle.decode(state.traderData) 
        if not isinstance(traderData, TraderData):
            raise ValueError("Invalid trader data")
        return traderData

    def apply_per_trading_strategy(self, trader_product_data: dict[str, ProductData], processed_market_orders: dict[str, CurrentMarketProductData]):
        product1 = "SQUID_INK"
        product2 = "KELP"
    

    def process_buy_orders(self, traderData, product, buy_orders, orders):
        volume_taken, avg_buy_price, last_buy_price = self.calculate_buy_market_price(buy_orders)

        is_profitable = avg_buy_price - traderData.position.avg_price >= SELL_PRICE_MARGIN and avg_buy_price - traderData.average.price >= SELL_PRICE_MARGIN

        if volume_taken > 0 and traderData.position.check_trade_allowed(-volume_taken) and is_profitable:
                # send sell order at last market price we want to match
            print("SELL", str(-volume_taken) + "xox", last_buy_price)
            order = Order(product, last_buy_price, -volume_taken)
            orders.append(order)
        else:
            print(f"WON'T SELL because market profit margin price is {avg_buy_price - traderData.average.price} and my limit is {SELL_PRICE_MARGIN}")

    def calculate_buy_market_price(self, buy_orders):
        index = 0
        volume_taken = 0
        avg_buy_price = 0
        last_buy_price = None
        while index < len(buy_orders) and volume_taken < TRADE_VOLUME:
            temp_volume = min(TRADE_VOLUME - volume_taken, buy_orders[index][1])
            avg_buy_price += buy_orders[index][0] * temp_volume
            volume_taken += temp_volume
            last_buy_price = buy_orders[index][0]
            index += 1
        avg_buy_price /= volume_taken
        print(f"Market Buy price computed for volume = {volume_taken} is {avg_buy_price}")
        return volume_taken,avg_buy_price,last_buy_price

    def process_sell_orders(self, traderData, product, sell_orders, orders):
        """
        We should be able to find out the best trades that we can do instead of relying on the TRADE_VOLUME 
        """
        volume_taken, avg_sell_price, last_sell_price = self.calculate_sell_market_price(sell_orders)
        is_profitable =  traderData.position.avg_price - avg_sell_price >= BUY_PRICE_MARGIN and  traderData.average.price - avg_sell_price >= BUY_PRICE_MARGIN

        if volume_taken > 0 and traderData.position.check_trade_allowed(volume_taken) and is_profitable:
            # send buy order at last market price we want to match
            print("BUY", str(volume_taken) + "xox", last_sell_price)
            order = Order(product, last_sell_price, volume_taken)
            orders.append(order)
        else:
            print(f"WON'T BUY because market profit margin price is {traderData.average.price - avg_sell_price} and my limit is {BUY_PRICE_MARGIN}")

    def calculate_sell_market_price(self, sell_orders):
        """
        Calculate the market price for selling a given volume of orders.

        <p>TODO: <br>
        We should be able to find out the best trades that we can do instead of relying on the TRADE_VOLUM
        """
        index = 0
        volume_taken = 0
        avg_sell_price = 0
        last_sell_price = None
        while index < len(sell_orders) and volume_taken < TRADE_VOLUME:
            temp_volume = min(TRADE_VOLUME - volume_taken, sell_orders[index][1])
            avg_sell_price += sell_orders[index][0] * temp_volume
            volume_taken += temp_volume
            last_sell_price = sell_orders[index][0]
            index += 1
        avg_sell_price /= volume_taken
        print(f"Market Sell price computed for volume = {volume_taken} is {avg_sell_price}")
        return volume_taken,avg_sell_price,last_sell_price

    def sort_market_orders(self, order_depth):
        sell_orders = list(order_depth.sell_orders.items())
        sell_orders = [(sell_order[0], abs(sell_order[1])) for sell_order in sell_orders]
        sell_orders.sort(key=lambda x: (-x[0], x[1]))

        print("Sell side:")
        print("Price : Volume")
        for sell_order in sell_orders:
            print(f"{sell_order[0]} : {sell_order[1]}")
        
        buy_orders = list(order_depth.buy_orders.items())
        buy_orders.sort(key=lambda x: (-x[0], x[1]))

        print("Buy side:")
        print("Price : Volume")
        for buy_order in buy_orders:
            print(f"{buy_order[0]} : {buy_order[1]}")
        return sell_orders,buy_orders