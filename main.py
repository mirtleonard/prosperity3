from trader import Trader
from datamodel import OrderDepth, UserId, TradingState, Order, Listing, Trade
from typing import List
import datetime

trader = Trader()
rsn_order_depth = OrderDepth()
rsn_order_depth.buy_orders = {100: 10, 101: 20, 102: 30}
rsn_order_depth.sell_orders = {105: 5, 106: 15, 107: 25}
klp_order_depth = OrderDepth()
klp_order_depth.buy_orders = {200: 10, 201: 20, 202: 30}
klp_order_depth.sell_orders = {205: 5, 206: 15, 207: 25}

result, conversions, traderData = trader.run(
    TradingState(
    "",
    datetime.time,
    {
        "RAINFOREST_RESIN": Listing("RSN", "RAINFOREST_RESIN", "SEASHELLS"),
        "KELP": Listing("KLP", "KELP", "SEASHELLS"),
    }, 
    {
        "RSN": rsn_order_depth,
        "KLP": klp_order_depth,
    },
    { # own trades
        "RSN":[],
        "KLP": [],
    }, 
    { # market trades
        "RSN": [
            Trade("RSN", 100, 10, "user1", "user2", datetime.time()),
        ],
        "KLP": [
            Trade("KLP", 200, 20, "user3", "user4", datetime.time()),
        ],
    },
    { # positions
        "RSN": 2,
        "KLP": 3,
    },
    {}
))
print(result)
print("here: " + traderData)
result, c, t = trader.run(
    TradingState(
        traderData,
        datetime.time,
    {
        "RAINFOREST_RESIN": Listing("RSN", "RAINFOREST_RESIN", "SEASHELLS"),
        "KELP": Listing("KLP", "KELP", "SEASHELLS"),
    }, 
    {
        "RSN": rsn_order_depth,
        "KLP": klp_order_depth,
    },
    { # own trades
        "RSN":[],
        "KLP": [],
    }, 
    { # market trades
        "RSN": [
            Trade("RSN", 100, 10, "user1", "user2", datetime.time()),
        ],
        "KLP": [
            Trade("KLP", 200, 20, "user3", "user4", datetime.time()),
        ],
    },
    { # positions
        "RSN": 2,
        "KLP": 3,
    },
    {}
    )
)
print (result)
print (t)