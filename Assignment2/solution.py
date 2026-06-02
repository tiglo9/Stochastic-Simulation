from numpy.random import exponential
from numpy import std, sqrt
import matplotlib.pyplot as plt
import scipy

from core import *
from math import pi, sin, cos, e
from numpy import random
import numpy as np
from statistics import *

regenerative = False
v_1 = False
v_2 = False
if v_2:
    v_1 = True

class Book:
    def __init__(self, sim: Simulation):
        self.m = 100


        self.lambda_0 = 5
        self.lambda_min =0.5
        self.alpha = 0.05
        self.q_limit = 0.7
        self.v_bar = 10
        self.delta_bar = 0.5
        self.tau_bar = 60
        self.m_star = 100
        self.delta_max = 5
        self.kappa = 0.1
        self.eta = 0.02
        self.arrival_rate = self.lambda_0 * np.exp(-self.alpha * (self.m - self.m_star) ** 2) + self.lambda_min

        self.stats_archive = []
        self.stats = Statistics(sim.current_time)
        self.last_batch_end = 0
        self.sim = sim
        self.next_arrival = None
        self.bidq = []
        self.askq = []
        self.n_batches = 0
        self.max_batches = 50
        self.warm_up_time = 180
        self.batch_length = 4*self.warm_up_time

        self.nr_trades = 0
        self.warmed_up = False

        self.l = 0
        self.mu = 0
        global v_1
        global v_2
        if v_1:
            self.alpha = 0
            self.eta = 0
            self.l = 0.5
            self.mu = 1
            self.arrival_rate = self.l + self.mu
            if v_2:
                self.arrival_rate = 0.5

    def get_bid(self):
        return max(self.bidq, key=lambda o: (o.price, -o.time))

    def get_ask(self):
        return min(self.askq, key=lambda o: (o.price, o.time))

    def add_order(self, order):
        if len(self.askq) == 0 and len(self.bidq) == 0:
            pass#print('empty book')

        if order.bid:
            self.bidq.append(order)
        else:
            self.askq.append(order)
        if len(self.bidq) == 1:
            global v_1, v2
            if v_1:
                self.stats.waiting_times.record(0)
                if v_2:
                    self.sim.schedule(V2Service(self.sim.current_time + 1 / self.mu, self, self.bidq[0]))
        self.record_ba_spread()


    def process_market_order(self, is_buy):
        self.stats.total_market_orders += 1
        if is_buy:
            if len(self.askq) != 0:
                self.execute_trade(False, self.get_ask(), 1)
            else:
                self.stats.rejected_market_orders += 1
        else:
            if len(self.bidq) != 0:
                self.execute_trade(self.get_bid(), False, -1)
                global v_1
                if v_1 and self.bidq:
                    self.stats.waiting_times.record(self.sim.current_time - self.bidq[0].time)
            else:
                self.stats.rejected_market_orders += 1

    def price_process(self, v):
        if abs(self.m - self.m_star) > self.delta_max:
            # Mean reversion
            self.m += self.eta * v - self.kappa*(self.m - self.m_star)
        else:
            self.m += self.eta * v
        self.update_arrival_rate()

    def update_arrival_rate(self):
        global v_1
        if v_1:
            return
        self.arrival_rate = self.lambda_0 * np.exp(-self.alpha*(self.m-self.m_star)**2) + self.lambda_min
        self.sim.cancel(self.next_arrival)
        self.next_arrival.schedule_next(self.sim)
        self.stats.arrival_rate_ts[0].append(self.sim.current_time)
        self.stats.arrival_rate_ts[1].append(self.arrival_rate)

    def match(self, order):
        if order.bid:
            if len(self.askq) != 0:
                other = self.get_ask()
                if order.price >= other.price:
                    self.execute_trade(order, other, 1)
            else:
                return
        else:
            if len(self.bidq) != 0:
                other = self.get_bid()
                if order.price <= other.price:
                    self.execute_trade(other, order, -1)
            else:
                return
    def execute_trade(self, buy, sell, dir):
        global regenerative
        if sell:
            self.askq.remove(sell)
            self.sim.cancel(sell.cancel_event)
            self.stats.accepted_limit_orders += 1
            self.stats.time_to_fill.record(self.sim.current_time - sell.time)
        if buy:
            self.bidq.remove(buy)
            self.sim.cancel(buy.cancel_event)
            self.stats.accepted_limit_orders += 1
            self.stats.time_to_fill.record(self.sim.current_time - buy.time)
        self.nr_trades += 1
        if self.warmed_up == False and self.sim.current_time >= self.warm_up_time and not regenerative:
            self.warmed_up = True
            self.stats=Statistics(sim.current_time)
            self.last_batch_end = self.sim.current_time
        if self.sim.current_time > self.warm_up_time and self.sim.current_time - self.last_batch_end >= self.batch_length and not regenerative:
            print(self.stats.return_stats(self.sim.current_time))
            self.stats_archive.append(self.stats.return_stats(self.sim.current_time))
            self.stats = Statistics(sim.current_time)
            self.last_batch_end = self.sim.current_time
            self.n_batches += 1
        if regenerative and self.sim.current_time != 0:
            if not self.bidq and not self.askq:
                if abs(self.m - self.m_star) < 2.5:
                    print('cycle!')
                    self.stats_archive.append(self.stats.return_stats(sim.current_time))
                    print(self.stats.return_stats(self.sim.current_time)["vol"])
                    self.stats = Statistics(sim.current_time)
                    self.n_batches += 1
        if self.n_batches >= self.max_batches:
            sim.stop()
        self.price_process(dir * exponential(self.v_bar))
        self.record_ba_spread()

    def record_ba_spread(self):
        if len(self.bidq) == 0 or len(self.askq) == 0:
            self.stats.bid_ask_spread.append((self.sim.current_time, None))
        else:
            self.stats.bid_ask_spread.append((self.sim.current_time, self.get_ask().price - self.get_bid().price))

class LimitOrder:
    def __init__(self, price, time, bid):
        self.cancel_event = None
        self.price = price
        self.time = time
        self.bid = bid

    def set_cancel_event(self, cancel_event):
        self.cancel_event = cancel_event

    def __repr__(self):
        return f"{"Bid" if self.bid else "Ask"} order ({self.price}, {self.time})"

class CancelEvent(Event):
    def __init__(self, time, book, order):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.book = book
        self.order = order
    def execute(self, sim: "Simulation") -> None:
        global v_1
        if v_1:
            return
        self.book.stats.cancelled_limit_orders += 1
        if self.order.bid:
            self.book.bidq.remove(self.order)
        else:
            self.book.askq.remove(self.order)
        self.book.record_ba_spread()

class OrderArrival(Event):
    def __init__(self, time, book):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.book = book


    def execute(self, sim: "Simulation") -> None:
        global v_1
        self.schedule_next(sim)
        if (random.random() < self.book.q_limit and not v_1) or (random.random() < self.book.l / self.book.arrival_rate and v_1) or v_2:
            # Arrival is a limit order
            delta_n = random.exponential(self.book.delta_bar)
            is_bid = random.random() < 0.5
            if v_1:
                is_bid = True
            if is_bid:
                # Arrival is a bid limit order
                price = self.book.m - delta_n
                if v_1:
                    price = 100

                if price <= 0:
                    # Order rejected as invalid
                    return
            else:
                # Arrival is an ask limit order
                price = self.book.m + delta_n

            order = LimitOrder(price, self.time, is_bid)
            tau = random.exponential(self.book.tau_bar)
            cancel_event = CancelEvent(self.time + tau, self.book, order)
            order.set_cancel_event(cancel_event)

            sim.schedule(cancel_event)
            self.book.add_order(order)
            self.book.match(order)

        else:
            # Arrival is a market order
            is_buy = random.random() < 0.5
            if v_1:
                is_buy = False
            self.book.process_market_order(is_buy)

    def schedule_next(self, sim):
        time = sim.current_time + exponential(1/self.book.arrival_rate)
        next_arrival = OrderArrival(time, self.book)
        sim.schedule(next_arrival)
        self.book.next_arrival=next_arrival

class V2Service(Event):
    def __init__(self, time, book, order):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.book = book
        self.order = order

    def execute(self, sim: "Simulation") -> None:
        self.book.bidq.remove(self.order)
        self.book.nr_trades += 1
        if self.book.nr_trades > 50000:
            print(self.book.stats.waiting_times.mean())
            sim.stop()
        if self.book.bidq:
            sim.schedule(V2Service(sim.current_time+1/self.book.mu, self.book, self.book.bidq[0]))
            self.book.stats.waiting_times.record(sim.current_time-self.book.bidq[0].time)

class SampleMarketVolitility(Event):
    def __init__(self, time, book):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.book = book
    def execute(self, sim: "Simulation") -> None:
        sim.schedule(SampleMarketVolitility(sim.current_time + 1, self.book))
        book.stats.price.append(self.book.m)

class Statistics:
    def __init__(self, time):
        self.start_time = time
        self.bid_ask_spread = []
        self.time_to_fill = SampleStatistic()
        self.waiting_times = SampleStatistic()
        self.cancelled_limit_orders = 0
        self.accepted_limit_orders = 0
        self.price = []
        self.arrival_rate_ts = [[],[]]
        self.total_market_orders = 0
        self.rejected_market_orders = 0

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

    def return_stats(self, time):
        result = {}
        result["ta b-a spread"] = self.avg_bid_ask_spread(time)
        result["ttf"] = self.time_to_fill.mean()
        global v_1
        if v_1:
            result["Wq"] = self.waiting_times.mean()
        result["cr"] = self.cancelled_limit_orders / (time-self.start_time)
        result["rr"] = self.rejected_market_orders / (time-self.start_time)


        log_returns = []
        prices = self.price
        for i in range(len(prices) - 1):
            if prices[i] > 0 and prices[i + 1] > 0 and prices[i] != prices[i + 1]:
                log_returns.append(np.log(prices[i + 1] / prices[i]))

        vol = np.std(log_returns)
        result["vol"] = vol

        plt.plot(self.arrival_rate_ts[0],self.arrival_rate_ts[1])
        plt.xlabel("Time")
        plt.ylabel("Arrival rate")
        #plt.show()
        return result


if __name__ == "__main__":
    #there are some settings at the top of the file

    sim = Simulation()
    book = Book(sim)
    arrival = OrderArrival(0, book)

    book.next_arrival = arrival
    sim.schedule(arrival)
    sim.schedule(SampleMarketVolitility(0, book))
    sim.run()

    ba_spreads = [stats["ta b-a spread"] for stats in book.stats_archive]
    ttf = [stats["ttf"] for stats in book.stats_archive]
    crs = [stats["cr"] for stats in book.stats_archive]
    rrs = [stats["rr"] for stats in book.stats_archive]
    vol = [stats["vol"] for stats in book.stats_archive]
    def calculate_r(l):
        if v_2:
            return
        r = len(l)
        delta = 0.05
        t = scipy.stats.t.ppf(1 - 0.05/2, r - 1)
        print('is it true?')
        print(r >= t**2 * np.std(l, ddof=1)**2/(delta/(1+delta)*sum(l)/r)**2)

    #calculate_r(rrs)
    if not v_2:
        print(f"the time-averaged bid-ask spread is {sum(ba_spreads)/len(ba_spreads)} with 95% CI ({sum(ba_spreads)/len(ba_spreads)-1.96*std(ba_spreads, ddof=1)/sqrt(len(ba_spreads))},{sum(ba_spreads)/len(ba_spreads)+1.96*std(ba_spreads, ddof=1)/sqrt(len(ba_spreads))})")
        print(f"the average time to fill is {sum(ttf) / len(ttf)} with 95% CI ({sum(ttf) / len(ttf) - 1.96 * std(ttf, ddof=1) / sqrt(len(ttf))},{sum(ttf) / len(ttf) + 1.96 * std(ttf, ddof=1) / sqrt(len(ttf))})")
        print(f"the average cancellation rate is {sum(crs)/len(crs)} with 95% CI ({sum(crs)/len(crs)-1.96*std(crs, ddof=1)/sqrt(len(crs))},{sum(crs)/len(crs)+1.96*std(crs, ddof=1)/sqrt(len(crs))})")
        print(f"the average rejection rate is {sum(rrs) / len(rrs)} with 95% CI ({sum(rrs) / len(rrs) - 1.96 * std(rrs, ddof=1) / sqrt(len(rrs))},{sum(rrs) / len(rrs) + 1.96 * std(rrs, ddof=1) / sqrt(len(rrs))})")
        print(f"the average volatility is {sum(vol)/len(vol)}")
    if v_1:
        wq = [stats["Wq"] for stats in book.stats_archive]
        print(sum(wq)/len(wq))