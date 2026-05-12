from core import *
from math import pi, sin, cos, e
from numpy import random
from statistics import *


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
    sim.run()
