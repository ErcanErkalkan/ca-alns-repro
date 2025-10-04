
import random, math
from typing import Dict, Any, List
from ca_alns.eval import fitness_value, fitness_wrapped, EvalCounter

class DE:
    def __init__(self, fitness_penalties: dict, E_max: int, seed: int = 0, pop_size: int = 30, F: float = 0.5, CR: float = 0.8):
        self.penalties = fitness_penalties
        self.eval_counter = EvalCounter(E_max=E_max)
        self.rng = random.Random(seed)
        self.pop_size = pop_size
        self.F = F; self.CR = CR
        self.cache = {}

    def _vec(self, sol: Dict[str,Any]) -> float:
        return sol.get('total_travel', 100.0)

    def _from_vec(self, val: float, base: Dict[str,Any]) -> Dict[str,Any]:
        s = base.copy()
        s['total_travel'] = max(1e-3, val)
        return s

    def run(self, seed_sol: Dict[str,Any]) -> Dict[str,Any]:
        pop = [seed_sol.copy() for _ in range(self.pop_size)]
        scores = [fitness_wrapped(fitness_value, self.eval_counter, self.cache, ind, self.penalties) for ind in pop]
        best_idx = min(range(len(scores)), key=lambda i: scores[i])
        best = pop[best_idx].copy(); best['fitness'] = scores[best_idx]

        while self.eval_counter.used < self.eval_counter.E_max:
            for i in range(self.pop_size):
                if self.eval_counter.used >= self.eval_counter.E_max:
                    break
                idxs = [idx for idx in range(self.pop_size) if idx != i]
                a,b,c = self.rng.sample(idxs, 3)
                x = self._vec(pop[i]); va = self._vec(pop[a]); vb = self._vec(pop[b]); vc = self._vec(pop[c])
                trial_val = x if self.rng.random() > self.CR else (va + self.F*(vb - vc))
                trial = self._from_vec(trial_val, pop[i])
                J_trial = fitness_wrapped(fitness_value, self.eval_counter, self.cache, trial, self.penalties)
                if J_trial < scores[i]:
                    pop[i] = trial; scores[i] = J_trial
                    if J_trial < best['fitness']:
                        best = trial.copy(); best['fitness'] = J_trial
        best['E_used'] = self.eval_counter.used
        return best
