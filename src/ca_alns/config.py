
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class ConnectivityConfig:
    mode: str = "range"  # 'range' or 'sinr'
    R: float = 150.0
    rho: float = 15.0
    v_max: float = 15.0
    delta_tau: Optional[float] = None
    # SINR-specific
    tx_power_dbm: float = 20.0
    noise_dbm: float = -96.0
    gamma_th_db: float = 6.0
    bidirectional: bool = True

@dataclass
class OperatorConfig:
    T0_scale: float = 0.05
    alpha: float = 0.995
    block_len: int = 50
    weights_w1: float = 5.0
    weights_w2: float = 2.0
    weights_w3: float = 0.5
    k_regret: int = 2           # 2 or 3
    apply_local_search: bool = False
    use_rally_points: bool = True
    warm_blocks: int = 3
    p_warm: float = 1e-2

@dataclass
class BudgetConfig:
    E_max: int = 100000
    T_max: Optional[float] = None

@dataclass
class PenaltyConfig:
    alpha: float = 1.0
    lambda_disc: float = 0.0
    lambda_cap: float = 0.0
    lambda_bat: float = 0.0
    lambda_bal: float = 0.0
    lambda_wait: float = 0.0
    lambda_rp: float = 0.0
    lambda_mksp: float = 0.0
    H_max: Optional[float] = None
    phase: str = "warm"   # 'warm' or 'final'

@dataclass
class ExperimentConfig:
    connectivity: ConnectivityConfig
    operators: OperatorConfig
    budget: BudgetConfig
    penalties: PenaltyConfig
