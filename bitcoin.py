from numpy.f2py.auxfuncs import throw_error

from core import Simulation, Event
from statistics import SampleStatistic, TimeWeightedStatistic
from math import sin, cos, pi, e
import bisect

class Transaction:
    def __init__(self, n, at):
        self.size = 200 + 100 * abs(cos(n * pi / 7))
        self.fee = 500 + 300 * abs(sin(n * e / 2))
        self.fee_rate = self.fee / self.size
        self.n = n
        self.arrival_time = at
        self.had_rbf = False

    def __repr__(self):
        return str(self.size)

    def __lt__(self, other):
        #for deciding ties in the mempool
        return self.n < other.n

class Mempool:
    def __init__(self, stats):
        self.queue = []
        self.sim = None
        self.confirmed_transactions = 0
        self.stats = stats
        self.previous_mine_time = 0

    def set_simulation(self, sim):
        self.sim = sim

    def add_transaction(self, transaction: Transaction ):
        bisect.insort(self.queue, (transaction.fee_rate, transaction))
        self.stats.add_mempool_size(len(self.queue), transaction.arrival_time)

    def mine_block(self, time):
        block_size = 1_000_000
        while self.queue:
            fee_rate, transaction = self.queue.pop()
            if transaction.size <= block_size:
                block_size -= transaction.size
                self.confirmed_transactions += 1
                self.stats.add_confirmation_time(transaction, time)
                if self.confirmed_transactions >= 2000:
                    sim.stop()
            else:
                bisect.insort(self.queue, (fee_rate, transaction))
        self.stats.add_mempool_size(len(self.queue), time)
        self.stats.add_block_utilization(1-(block_size/1_000_000))
        print(f"there were {block_size} bits left")

    def RBF(self, transaction):
        for i in range(len(self.queue)):
            if self.queue[i][1] == transaction:
                self.queue.pop(i)
                transaction.fee *= 1.5
                transaction.fee_rate *= 1.5
                transaction.had_rbf = True
                self.add_transaction(transaction)
                break

class RBF(Event):
    def __init__(self, time, transaction, mempool):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.transaction = transaction
        self.mempool = mempool

    def execute(self, sim: "Simulation") -> None:
        self.mempool.RBF(self.transaction)

class TransactionArrival(Event):
    def __init__(self, n, time, mempool):
        self.time: float = time
        self.cancelled: bool = False
        self.n = n
        self._seq: int = 0  # set by Simulation.schedule()
        self.mempool = mempool

    def execute(self, sim: "Simulation") -> None:
        #print(f"new transaction arrived with { 200 + 100 * abs(cos(self.n * pi / 7))} bits")
        dt = 8 * (2 + sin(self.n * pi / 5))

        new_transaction = Transaction(self.n, self.time)
        self.mempool.add_transaction(new_transaction)
        RBF_event = RBF(self.time + 180, new_transaction, self.mempool)
        sim.schedule(RBF_event)

        sim.schedule(TransactionArrival(self.n + 1,
                                        self.time + dt,
                                        self.mempool))

class BlockMiningEvent(Event):
    def __init__(self, time, mempool):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.mempool = mempool


    def execute(self, sim: "Simulation") -> None:
        print(f"started mining a new block at {self.time}")
        self.mempool.mine_block(self.time)
        sim.schedule(BlockMiningEvent(self.time + 600, self.mempool))
        print(f"the mempool has {len(self.mempool.queue)} available transactions\n")

class Statistics:
    def __init__(self):
        self.avg_confirmation_time = SampleStatistic()
        self.avg_confirmation_time_RBF = SampleStatistic()
        self.avg_confirmation_time_NORBF = SampleStatistic()
        self.avg_mempool_size = TimeWeightedStatistic()
        self.avg_block_utilization = SampleStatistic()

    def add_confirmation_time(self, transaction, t):
        self.avg_confirmation_time.record(t-transaction.arrival_time)
        if transaction.had_rbf:
            self.avg_confirmation_time_RBF.record(t-transaction.arrival_time)
        else:
            self.avg_confirmation_time_NORBF.record(t-transaction.arrival_time)

    def add_mempool_size(self, n, t):
        self.avg_mempool_size.update(t, n)

    def add_block_utilization(self, util):
        self.avg_block_utilization.record(util)

if __name__ == "__main__":
    sim = Simulation()  
    stats = Statistics()
    mempool = Mempool(stats)
    mempool.set_simulation(sim)
    sim.schedule(TransactionArrival(0, 0, mempool))
    sim.schedule(BlockMiningEvent(600, mempool))
    sim.run()
    print("average mempool size:", stats.avg_mempool_size.mean(sim.current_time))
    print("average block utilization:", stats.avg_block_utilization.mean())
    print("average confirmation time:", stats.avg_confirmation_time.mean())
    print("average confirmation time NORBF:", stats.avg_confirmation_time_NORBF.mean())
    print("average confirmation time RBF:", stats.avg_confirmation_time_RBF.mean())


