# des_library

Reusable Discrete Event Simulation (DES) library designed for teaching and project work.

The library is modular, object-oriented, and fully encapsulated (no global simulation state), so it can be reused across domains such as healthcare, finance, logistics, energy, and operations.

## Features

- Event-driven simulation engine with priority event list (heap)
- Event cancellation support (for stale timeout/cancellation events)
- Hook system before/after each event
- Time-weighted and sample-based statistics
- Common stochastic and deterministic distributions
- Clean API for building domain-specific simulation models

## Package Structure

```text
des_library/
├── __init__.py
├── core.py           # Simulation engine and Event base class
├── statistics.py     # TimeWeightedStatistic, SampleStatistic, Counter
├── distributions.py  # Deterministic, Exponential, Erlang, Uniform, Normal, Sequence
└── examples/
    ├── mm1.py        # M/M/1 example
    └── mg1ps.py      # M/G/1 Processor Sharing example
```

## Core API

### `Simulation`

Main simulation engine.

Key methods:
- `schedule(event)` -> insert event in event list
- `cancel(event)` -> mark event as cancelled
- `run(stop_condition=None)` -> start event loop
- `stop()` -> terminate simulation
- `reset()` -> clear state

Key attributes:
- `current_time`
- `previous_time`
- `pending_event_count`

### `Event`

Base class for all events. Subclass it and override:

```python
def execute(self, sim: Simulation) -> None:
    ...
```

Events have:
- `time`
- `cancel()`
- `active` property (`False` when cancelled)

### `StopSimulation`

Utility event that calls `sim.stop()` when executed.

## Statistics API

### `TimeWeightedStatistic`

For metrics like average queue length or server utilization.

Methods:
- `update(current_time, new_value)`
- `mean(current_time)`
- `accumulated(current_time)`

### `SampleStatistic`

For sample metrics like waiting time or service time.

Methods:
- `record(value)`
- `mean()`, `variance()`, `std()`
- `confidence_interval(confidence=0.95)`

### `Counter`

Simple counter utility.

Methods:
- `increment(n=1)`
- `rate(elapsed_time)`
- `fraction(total)`

## Distributions API

Available distribution wrappers (all expose `sample()` and are callable):

- `Deterministic(value)`
- `Exponential(mean)`
- `Erlang(k, mean)`
- `Uniform(low, high)`
- `Normal(mean, std)`
- `Sequence(func)`  (deterministic function-driven sequence)

Example:

```python
from des_library import Exponential

service_time = Exponential(mean=2.0)
x = service_time()   # same as service_time.sample()
```

## Minimal Example

```python
from des_library import Simulation, Event


class Arrival(Event):
    def execute(self, sim):
        print(f"Arrival at t={sim.current_time:.2f}")
        if sim.current_time < 10:
            sim.schedule(Arrival(sim.current_time + 1.5))
        else:
            sim.stop()


sim = Simulation()
sim.schedule(Arrival(0.0))
sim.run()
```

## Design Principles

- Encapsulation first: all state belongs to your model object(s)
- Event-centric logic: domain behavior is expressed as event classes
- Composability: simulation engine independent from domain models
- Extensibility: easy to add custom events, distributions, and statistics
- Reproducibility: set random seeds in application scripts

## Typical Workflow

1. Create a domain model class (state variables + statistics)
2. Define event classes that mutate model state
3. Schedule initial events
4. Run simulation until target horizon/condition
5. Report metrics from statistics collectors

## Examples
Reference examples are also included in:
- `des_library/examples/mm1.py`
- `des_library/examples/mg1ps.py`

## Notes

- The library is dependency-light (standard Python library only).
- Type hints are included for readability and maintainability.
- Python 3.9+ recommended.

