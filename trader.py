from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string
import jsonpickle
      
class TraderStatus:
    STARTED = 1
    BOUGHT = 2

POSITION_VOLUME_LIMIT = 50
AVERAGE_WINDOW_SIZE = 100
DISCOUNT_FACTOR = 0.9
BUY_PRICE_MARGIN = 1
SELL_PRICE_MARGIN = 1
TRADE_VOLUME = 1

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

class TraderData:
    def __init__(self):
        self.iteration = 1
        self.average = Average()
        self.position = TraderPosition()
        self.status = TraderStatus.STARTED
        
    def update(self, trade_prices, new_orders):
        self.iteration += 1
        for trade_price in trade_prices:
            self.average.update(trade_price)
        for order in new_orders:
            self.position.update(order.price, order.quantity)

class Average:
    def __init__(self):
        self.price = None
        self.samples = 0
        
    def update(self, price):
        if self.price is None:
            self.price = price
        self.price = self.price * DISCOUNT_FACTOR + price * (1 - DISCOUNT_FACTOR)
        self.samples += 1
    
    def is_good_approximation(self):
        return self.samples >= AVERAGE_WINDOW_SIZE

class Trader:
    """
    TODO:
    - When selling or buying we should take into account the other side also
    - We can also add propotionality to the volume we want to trade depending on how big is the spred between average and current
    """
    def run(self, state: TradingState):
        if not state.traderData:
            traderData = TraderData()
        else:
            traderData = jsonpickle.decode(state.traderData)
        print(f"TraderDataObj - iteration: {traderData.iteration}")

        # check all order book -- see how large it is
        product = "KELP"
        order_depth: OrderDepth = state.order_depths[product]
        sell_orders, buy_orders = self.sort_market_orders(order_depth)
            
        orders: list[Order] = []
        if traderData.average.is_good_approximation():
            # compute sell market price for volume = TRADE_VOLUME
            self.process_sell_orders(traderData, product, sell_orders, orders)
            # compute buy market price for volume = TRADE_VOLUME
            self.process_buy_orders(traderData, product, buy_orders, orders)

        result = {}
        for key in state.order_depths.keys():
            result[key] = []
        result[product] = orders

        trade_prices = []
        # print trades
        if state.market_trades:
            trades = state.market_trades[product]
            print("Trades:")
            print("Price : Volume")
            for trade in trades:
                print(f"{trade.price} : {trade.quantity}")
            
            trade_prices = [trade.price for trade in trades]
            print(f"Current avg is {traderData.average.price} and is it good approx? {traderData.average.is_good_approximation()}")
            print(f"Current position we have is {traderData.position.volume} volume of {product} bought at avg price {traderData.position.avg_price}")

        traderData.update(trade_prices, orders)

        return result, 1, jsonpickle.encode(traderData)

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