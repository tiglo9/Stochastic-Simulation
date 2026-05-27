from core import Event, Simulation
from numpy.random import exponential
queue = []
l = 0.5
m = 1
w = []
w_q = []
class BuyOrderArrival(Event):
    def execute(self, sim: "Simulation") -> None:
        queue.append([sim.current_time, None])
        if len(queue) == 1:
            queue[0][1] = sim.current_time
        sim.schedule(BuyOrderArrival(sim.current_time+exponential(1/l)))

class SellArrival(Event):
    def execute(self, sim: "Simulation") -> None:
        if len(queue) > 0:
            buy = queue.pop(0)
            w.append(sim.current_time-buy[0])
            w_q.append(sim.current_time-buy[1])
            if len(queue) > 0:
                queue[0][1] = sim.current_time
        sim.schedule(SellArrival(sim.current_time+1/m))


sim = Simulation()
sim.schedule(BuyOrderArrival(exponential(1/l)))
sim.schedule(SellArrival(1/m))
sim.run(stop_condition=lambda sim:sim._event_counter == 500000)
print(sum(w)/len(w))
print(sum(w_q)/len(w_q))
