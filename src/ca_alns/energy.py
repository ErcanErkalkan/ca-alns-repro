
import time
from contextlib import contextmanager

@contextmanager
def energy_session():
    """A portable stub: measures elapsed time and returns a crude energy estimate if RAPL/GPU not available.
    In real use, integrate Intel RAPL / NVML. Here we assume a configurable average power (W).
    """
    t0 = time.time()
    try:
        yield
    finally:
        pass

def measure_energy_wh(run_fn, avg_power_w: float = 50.0):
    """Run a function while measuring elapsed time; estimate energy = avg_power_w * elapsed_hours.
    Returns (result, energy_Wh).
    """
    t0 = time.time()
    with energy_session():
        result = run_fn()
    dt = time.time() - t0
    E_wh = avg_power_w * (dt / 3600.0)
    return result, E_wh
