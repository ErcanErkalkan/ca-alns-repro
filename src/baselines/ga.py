
import random, math
from typing import Dict, Any, List
from ca_alns.eval import fitness_value, fitness_wrapped, EvalCounter

class GA:
    def __init__(self, fitness_penalties: dict, E_max: int, seed: int = 0, pop_size: int = 50, p_mut: float = 0.1):
        self.penalties = fitness_penalties
        self.eval_counter = EvalCounter(E_max=E_max)
        self.rng = random.Random(seed)
        self.pop_size = pop_size
        self.p_mut = p_mut
        self.cache = {}

    def _mutate(self, sol: Dict[str,Any]) -> Dict[str,Any]:
        s = sol.copy()
        if self.rng.random() < 0.5:
            s['total_travel'] = sol.get('total_travel', 100.0) * (0.95 + 0.1*self.rng.random())
        return s

    def run(self, seed_sol: Dict[str,Any]) -> Dict[str,Any]:
        pop = [seed_sol.copy() for _ in range(self.pop_size)]
        scores = [fitness_wrapped(fitness_value, self.eval_counter, self.cache, ind, self.penalties) for ind in pop]
        best_idx = min(range(len(scores)), key=lambda i: scores[i])
        best = pop[best_idx].copy(); best['fitness'] = scores[best_idx]
        while self.eval_counter.used < self.eval_counter.E_max:
            i,j = self.rng.randrange(self.pop_size), self.rng.randrange(self.pop_size)
            parent = pop[i] if scores[i] < scores[j] else pop[j]
            child = self._mutate(parent)
            J = fitness_wrapped(fitness_value, self.eval_counter, self.cache, child, self.penalties)
            # replace worst
            worst_idx = max(range(len(scores)), key=lambda k: scores[k])
            pop[worst_idx] = child; scores[worst_idx] = J
            if J < best['fitness']:
                best = child.copy(); best['fitness'] = J
        best['E_used'] = self.eval_counter.used
        return best
