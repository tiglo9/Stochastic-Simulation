from core import *
from math import pi, sin, cos, e
from random import random, seed
from statistics import *

seed(67)


class MatchingEngine:
    def __init__(self, sim):
        self.bidq = []
        self.askq = []
        self.n_trades = 0
        self.sim = sim
        self.stats = Statistics()

    def add_bid(self, order, time):
        self.bidq.append(order)

        if len(self.bidq) != 0 and len(self.askq) != 0:
            self.stats.bid_ask_spread.append((time, self.get_ask().price - self.get_bid().price))

        self.stats.bid_length.update(time, len(self.bidq))

    def add_ask(self, order, time):
        self.askq.append(order)

        if len(self.bidq) != 0 and len(self.askq) != 0:
            self.stats.bid_ask_spread.append((time, self.get_ask().price - self.get_bid().price))

        self.stats.ask_length.update(time, len(self.askq))

    def get_bid(self):
        return (max(self.bidq, key=lambda x: x.price))

    def get_ask(self):
        return (min(self.askq, key=lambda x: x.price))

    def cancel_order(self, order, time):
        if order.bid:
            self.bidq.remove(order)
            self.stats.bid_length.update(time, len(self.bidq))
            if len(self.bidq) == 0 or len(self.askq) == 0:
                self.stats.bid_ask_spread.append((time, None))
            else:
                self.stats.bid_ask_spread.append((time, self.get_ask().price - self.get_bid().price))

        else:
            self.askq.remove(order)
            self.stats.ask_length.update(time, len(self.askq))
            if len(self.bidq) == 0 or len(self.askq) == 0:
                self.stats.bid_ask_spread.append((time, None))
            else:
                self.stats.bid_ask_spread.append((time, self.get_ask().price - self.get_bid().price))
        self.stats.cancelled += 1

    def handle_market_order(self, time):
        if random() > .5:
                                                        # 'Vo
            # Case sell
            if len(self.bidq) == 0:
                return
            order = self.get_bid()
            self.accept_orders([order], time)
            # print(f"market bought {order.price}")
        else:
            # Case buy
            if len(self.askq) == 0:
                return
            order = self.get_ask()
            self.accept_orders([order], time)
            # print(f"market sold {order.price}")

    def check_match(self, time):
        if len(self.askq) == 0 or len(self.bidq) == 0:
            return
        bid = self.get_bid()
        ask = self.get_ask()
        if bid.price >= ask.price:
            # Match is made
            self.accept_orders([bid, ask], time)
            # print(f"matched bid {bid.price}, ask {ask.price}")

    def accept_orders(self, orders, time):
        for order in orders:
            order.cancel_event.cancel()
            if order.bid:
                self.bidq.remove(order)
                self.stats.bid_length.update(time, len(self.bidq))
            else:
                self.askq.remove(order)
                self.stats.ask_length.update(time, len(self.askq))

            self.stats.time_to_fill.record(time - order.time)
            self.stats.matched += 1
        if len(self.bidq) != 0 and len(self.askq) != 0:
            self.stats.bid_ask_spread.append((time, self.get_ask().price - self.get_bid().price))
        else:
            self.stats.bid_ask_spread.append((time, None))
        self.n_trades += 1
        if self.n_trades >= 500:
            self.sim.stop()


class LimitOrder:
    def __init__(self, price, bid, time):
        self.price = price
        self.cancel_event = None
        self.bid = bid
        self.time = time

    def set_cancel_event(self, cancel_event):
        self.cancel_event = cancel_event

    def __repr__(self):
        return str(self.price)


class CancelEvent(Event):
    def __init__(self, time: float, order, mengine):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.order = order
        self.mengine = mengine

    def execute(self, sim: "Simulation") -> None:
        # print("cancelled event", self.order.price)
        if self.order.bid:
            # print(self.mengine.bidq)
            pass
        else:
            # print(self.mengine.askq)
            pass
        self.mengine.cancel_order(self.order, self.time)
        self.mengine.check_match(self.time)


class OrderArrival(Event):
    def __init__(self, time: float, n, mengine):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.n = n
        self.mengine = mengine

    def execute(self, sim: "Simulation") -> None:
        dt = 5 * (1 + abs(sin(self.n * pi / 3)))
        new_order_arrival = OrderArrival(self.time + dt, self.n + 1, self.mengine)
        sim.schedule(new_order_arrival)
        if random() < .7:
            # Case limit order
            bid = random() < .5  # 50% chance for bid/ask
            limit_price = round(100 + 2 * sin(self.n * e), 2)
            tau = self.time + 30 * (1 + cos(self.n) ** 2)
            limit_order = LimitOrder(limit_price, bid, self.time)
            cancel_event = CancelEvent(tau, limit_order, self.mengine)
            limit_order.set_cancel_event(cancel_event)
            sim.schedule(cancel_event)
            if bid:
                self.mengine.add_bid(limit_order, self.time)
            else:
                self.mengine.add_ask(limit_order, self.time)

        else:
            # case market order
            self.mengine.handle_market_order(self.time)

        self.mengine.check_match(self.time)


class Statistics:
    def __init__(self):
        self.bid_ask_spread = []
        self.time_to_fill = SampleStatistic()
        self.cancelled = 0
        self.matched = 0
        self.bid_length = TimeWeightedStatistic()
        self.ask_length = TimeWeightedStatistic()

    def avg_bid_ask_spread(self, time):
        last_t = 0
        last_v = 0
        total_t = 0
        total_v = 0
        for t, v in self.bid_ask_spread:
            if last_v is not None:
                total_t += t - last_t
                total_v += (t - last_t) * last_v
            last_v = v
            last_t = t
        if last_v is not None:
            total_t += time - last_t
            total_v += (time - last_t) * last_v
        return total_v / total_t

    def print_stats(self, time):
        print(f"the time-avg bid-ask spread is {self.avg_bid_ask_spread(time)}")
        print(f"the avg time to fill is {self.time_to_fill.mean()}")
        print(f"the cancellation rate is {self.cancelled / (self.matched + self.cancelled)}")
        print(f"the avg ask queue length is {self.ask_length.mean(time)}")
        print(f"the avg bid queue length is {self.bid_length.mean(time)}")


if __name__ == "__main__":
    sim = Simulation()
    mengine = MatchingEngine(sim)
    sim.schedule(OrderArrival(0, 1, mengine))
    sim.run()
    mengine.stats.print_stats(sim.current_time)
