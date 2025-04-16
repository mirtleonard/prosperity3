from datamodel import OrderDepth, UserId, TradingState, Order, Symbol
from typing import List
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
        
    def update(self, price, quantity = 1):
        print(f"Updating average with price: {price}, quantity: {quantity}")
        if len(self.prices_window) == 0:
            self.average_price = price
            return

        # Remove old samples if adding new ones would exceed window size
        while len(self.prices_window) > 0 and self.samples + quantity > self.window_size:
            old_price, old_quantity = self.prices_window[0]
            remove_quantity = min(old_quantity, self.samples + quantity - self.window_size)
            
            # Update average by removing contribution of samples being removed
            self.average_price = (self.average_price * self.samples - old_price * remove_quantity) / (self.samples - remove_quantity)
            
            self.samples -= remove_quantity
            if remove_quantity == old_quantity:
                self.prices_window.pop(0)
            else:
                self.prices_window[0] = (old_price, old_quantity - remove_quantity)

        added_quantity = min(self.window_size - self.samples, quantity)
        self.prices_window.append((price, added_quantity))
        self.average_price = (self.average_price * self.samples + added_quantity * price) / (self.samples + added_quantity)
        self.samples += added_quantity

    def is_good_approximation(self):
        return self.samples == self.window_size

class TraderPosition:
    def __init__(self, position_limit = POSITION_VOLUME_LIMIT):
        self.avg_price = 0
        self.volume = 0
        self.position_limit = position_limit

    def check_trade_allowed(self, volume):
        return abs(self.volume + volume) <= self.position_limit

    def get_max_sell(self):
        return self.position_limit + self.volume

    def get_max_buy(self):
        return self.position_limit - self.volume

    def update(self, price, volume):
        new_volume = volume + self.volume
        if new_volume != 0:
            self.avg_price = (price * volume + self.avg_price * self.volume) / new_volume
        self.volume = new_volume

class ProductData:
    def __init__(self, limit):
        self.average : Average = Average()
        self.position : TraderPosition = TraderPosition(limit)
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
        self.buy_available : int = 0
        self.sell_available : int = 0
        self.sell_average : Average = Average(1)
        self.buy_average : Average = Average(1)

    def update(self, order_price, order_volume):
        if order_volume > 0:
            self.buy_available += order_volume
            self.buy_average.update(order_price, order_volume)
        else:
            self.sell_available += -order_volume
            self.sell_average.update(order_price, -1 * order_volume)

class Basket:
    def __init__(self):
        pass 

class Spread:
    def __init__(self, to_buy = {}, to_sell = {}):
        self.to_buy : dict[Symbol, int] = to_buy
        self.to_sell : dict[Symbol, int] = to_sell
        self.profit : float = 0

    def update(self, market: dict[Symbol, CurrentMarketProductData]):
        normal = self.calculate_profit_for_current_market_data(market)
        reversed = self.calculate_profit_for_current_market_data(market, True)
        print(f"Normal: {normal}, Reversed: {reversed} for {self.to_buy} -> {self.to_sell}")
        if (reversed > normal):
            self.profit = reversed
            aux = self.to_sell
            self.to_sell = self.to_buy
            self.to_buy = aux
        else:
            self.profit = normal

    def calculate_profit_for_current_market_data(self, market_data : dict[Symbol, CurrentMarketProductData], reverse = False):
        reverse_sign = -1 if reverse else 1

        buy_side_notional = 0
        quantity_buy_side = 0
        for product, quantity in self.to_buy.items():
            if market_data.get(product) != None:
                buy_side_notional += market_data[product].sell_average.average_price * quantity
                quantity_buy_side += quantity
                
        buy_side_notional /= quantity_buy_side if quantity_buy_side > 0 else 1

        sell_side_notional = 0
        sell_side_quantity = 0
        for product, quantity in self.to_sell.items():
            if market_data.get(product) != None:
                sell_side_notional += market_data[product].buy_average.average_price * quantity
                sell_side_quantity += quantity

        sell_side_notional /= sell_side_quantity if sell_side_quantity > 0 else 1
        return (sell_side_notional * reverse_sign) - (buy_side_notional * reverse_sign)


available_spreads = [
    Spread(
        {"KELP": 1},
        {"SQUID_INK": 1}
    ), 
    Spread(
        {"PICNIC_BASKET1": 1},
        {
            "CROISSANTS": 6,
            "JAMS": 3,
            "DJEMBES": 1
         }
    ),
    Spread(
        {"PICNIC_BASKET2": 1},
        {
            "CROISSANTS": 4,
            "JAMS": 2,
        }
    ),
    Spread(
        {"PICNIC_BASKET1": 2},
        {
            "PICNIC_BASKET2": 3,
            "JAMS": 2,
        }
    ),
    Spread(
        {"PICNIC_BASKET1": 1},
        { 
            "PICNIC_BASKET2": 1,
            "CROISSANTS": 2,
            "DJEMBES": 1
        }
    )
]

POSITION_LIMITS = {
    'RAINFOREST_RESIN': 50,
    'KELP': 50, 
    'SQUID_INK': 50,
    'CROISSANTS': 250,
    'JAMS': 350,
    'DJEMBES': 60,
    'PICNIC_BASKET1': 60,
    'PICNIC_BASKET2': 100,
    'VOLCANIC_ROCK': 400,
    'VOLCANIC_ROCK_VOUCHER_9500': 200,
    'VOLCANIC_ROCK_VOUCHER_9750': 200,
    'VOLCANIC_ROCK_VOUCHER_10000': 200,
    'VOLCANIC_ROCK_VOUCHER_10250': 200,
    'VOLCANIC_ROCK_VOUCHER_10500': 200,   
}

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
        print(f"TraderData: {traderData}")
        processed_market_orders = self.process_market_orders(traderData.products, state.order_depths)
        print(f"Processed market orders: {processed_market_orders}")
        own_trades = self.apply_per_trading_strategy(traderData.products, processed_market_orders)
        return own_trades, 1, jsonpickle.encode(traderData)

    def process_market_orders(self, trader_product_data: dict[str, ProductData], current_market: dict[str, OrderDepth]): 
        processed_market_orders = {}
        for product in current_market.keys():
            order_depth: OrderDepth = current_market[product]
            if product not in trader_product_data:
                trader_product_data[product] = ProductData(POSITION_LIMITS[product])
            product_data: ProductData = trader_product_data[product]

            current_market_product = CurrentMarketProductData()
            current_market_product.sell_orders = sorted(list(order_depth.sell_orders.items()), key=lambda x: (x[0], abs(x[1])))
            current_market_product.buy_orders = sorted(list(order_depth.buy_orders.items()), key=lambda x: (-x[0], abs(x[1])))

            for order in order_depth.sell_orders.items():
                current_market_product.update(order[0], order[1])
                product_data.average.update(order)
            for order in order_depth.buy_orders.items():
                current_market_product.update(order[0], order[1])
                product_data.average.update(order)
            processed_market_orders[product] = current_market_product

        return processed_market_orders
            

    def load_trader_data(self, state):
        if not state.traderData:
            traderData = TraderData()
        else:
            traderData = jsonpickle.decode(state.traderData) 
        if not isinstance(traderData, TraderData):
            raise ValueError("Invalid trader data")
        return traderData

    def apply_per_trading_strategy(self, trader: dict[str, ProductData], market: dict[str, CurrentMarketProductData])-> dict[Symbol, Order]:
        for spread in available_spreads:
            spread.update(market)

        available_spreads.sort(key=lambda spread: spread.profit, reverse=True)
        orders = {}
        for spread in available_spreads:
            spread_orders = self.make_trades_for_spread(spread, market, trader)
            for order in spread_orders:
                print(f"Order: {order}")
                if order.symbol not in orders:
                    orders[order.symbol] = []
                orders[order.symbol].append(order)
        return orders

    def make_trades_for_spread(self, spread: Spread, market: dict[str, CurrentMarketProductData], trader: dict[str, ProductData]) -> list[Order]:
        max_volume = self.get_max_volume(spread, trader, market)
        print(f"Max volume for spread {spread}: {max_volume}")  
        return self.make_orders(spread, max_volume, market, trader) if max_volume > 0 else []

    def make_orders(self, spread: Spread, max_volume: int, market: dict[str, CurrentMarketProductData], trader: dict[str, ProductData]) -> list[Order]:
        orders = []
        for product, quantity in spread.to_buy.items():
            total_quantity = quantity * max_volume
            for market_order in market[product].sell_orders:
                order_price, order_volume = market_order
                order_volume = -order_volume
                order_volume = total_quantity if order_volume > total_quantity else order_volume
                trader[product].position.update(order_price, order_volume)
                orders.append(Order(product, order_price, order_volume))
                total_quantity -= order_volume
                if total_quantity == 0:
                    break

        for product, quantity in spread.to_sell.items():
            total_quantity = quantity * max_volume
            for market_order in market[product].buy_orders:
                order_price, order_volume = market_order
                order_volume = total_quantity if order_volume > total_quantity else order_volume
                trader[product].position.update(order_price, -order_volume)
                orders.append(Order(product, order_price, -order_volume))
                total_quantity -= order_volume
                if total_quantity == 0:
                    break
        return orders

    def get_max_volume(self, spread: Spread, trader: dict[str, ProductData], market: dict[str, CurrentMarketProductData]) -> int:
        max_volume = 100000
        for product, quantity in spread.to_buy.items():
            if product not in market:
                return 0
            print("quantity", quantity)
            print(f"Position limit for {product}: {trader[product].position.position_limit} {trader[product].position.volume}")
            max_volume = min(max_volume, int(trader[product].position.get_max_buy() / quantity))
            print(f"Available buy for {product}: {market[product].buy_available}")
            max_volume = min(max_volume, int(market[product].buy_available / quantity))

        for product, quantity in spread.to_sell.items():
            if product not in market:
                return 0
            print("quantity", quantity)
            print(f"Position limit for {product}: {trader[product].position.position_limit} {trader[product].position.volume}")
            max_volume = min(max_volume, int(trader[product].position.get_max_sell() / quantity))
            print(f"Available sell for {product}: {market[product].sell_available}")
            max_volume = min(max_volume, int(market[product].sell_available / quantity))
        return max_volume        

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
