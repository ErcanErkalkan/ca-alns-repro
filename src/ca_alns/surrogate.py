
import json, numpy as np
from pathlib import Path

class FrozenSurrogate:
    def __init__(self, w, b, tau, mu, sigma, band=0.05):
        self.w = np.array(w, dtype=float).reshape(-1)
        self.b = float(b)
        self.tau = float(tau)
        self.mu = np.array(mu, dtype=float).reshape(-1)
        self.sigma = np.array(sigma, dtype=float).reshape(-1)
        self.band = float(band)

    @staticmethod
    def load(path: str):
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        band = data.get("band", 0.05)
        return FrozenSurrogate(data["w"], data["b"], data["tau"], data["mu"], data["sigma"], band=band)

    def score(self, feats):
        z = (np.array(feats, dtype=float).reshape(-1) - self.mu) / np.maximum(self.sigma, 1e-9)
        s = 1.0 / (1.0 + np.exp(-(self.w @ z + self.b)))
        return float(s)

    def is_borderline(self, s):
        return abs(s - self.tau) < self.band
