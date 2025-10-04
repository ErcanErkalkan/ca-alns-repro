
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class Node:
    id: int
    x: float
    y: float

@dataclass
class UAV:
    id: int
    v_max: float = 15.0
    battery_max: float = 1e9
    capacity: float = 1e9

@dataclass
class Instance:
    depot: Node
    targets: List[Node]
    uavs: List[UAV]

def dist(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    return math.hypot(a[0]-b[0], a[1]-b[1])

@dataclass
class RouteItem:
    kind: str   # 'target' or 'rp' or 'depot'
    node_id: int
    x: float
    y: float
    wait: float = 0.0

@dataclass
class Solution:
    routes: Dict[int, List[RouteItem]] = field(default_factory=dict)

    def total_travel(self) -> float:
        total = 0.0
        for rid, route in self.routes.items():
            for i in range(len(route)-1):
                a = (route[i].x, route[i].y)
                b = (route[i+1].x, route[i+1].y)
                total += dist(a,b)
        return total

    def workload_extrema(self) -> Tuple[float,float]:
        vals = []
        for rid, route in self.routes.items():
            s = 0.0
            for i in range(len(route)-1):
                a = (route[i].x, route[i].y)
                b = (route[i+1].x, route[i+1].y)
                s += dist(a,b)
            vals.append(s)
        return (max(vals) if vals else 0.0, min(vals) if vals else 0.0)

    def makespan(self, uavs: List[UAV], v_default: float = 15.0) -> float:
        ms = 0.0
        for rid, route in self.routes.items():
            v = v_default
            t = 0.0
            for i in range(len(route)-1):
                a = (route[i].x, route[i].y); b = (route[i+1].x, route[i+1].y)
                seg = dist(a,b); t += seg / max(v,1e-6)
                t += route[i+1].wait
            ms = max(ms, t)
        return ms

def build_initial_solution(inst: Instance) -> 'Solution':
    routes: Dict[int, List[RouteItem]] = {}
    n_uav = len(inst.uavs)
    for u in inst.uavs:
        d = inst.depot
        routes[u.id] = [RouteItem('depot', d.id, d.x, d.y)]
    for idx, tgt in enumerate(inst.targets):
        u = inst.uavs[idx % n_uav]
        routes[u.id].append(RouteItem('target', tgt.id, tgt.x, tgt.y))
    for u in inst.uavs:
        d = inst.depot
        routes[u.id].append(RouteItem('depot', d.id, d.x, d.y))
    return Solution(routes=routes)

def simulate_snapshots(sol: 'Solution', inst: Instance, delta_tau: float, v_default: float = 15.0):
    timelines = {}
    horizon = 0.0
    for u in inst.uavs:
        route = sol.routes[u.id]
        t = 0.0
        pts = []
        pts.append((t, (route[0].x, route[0].y)))
        for i in range(len(route)-1):
            a = (route[i].x, route[i].y); b=(route[i+1].x, route[i+1].y)
            seg = dist(a,b); dt = seg / max(u.v_max, 1e-6)
            t += dt
            pts.append((t, b))
            if i+1 < len(route):
                w = route[i+1].wait
                if w>0: 
                    t += w
                    pts.append((t, b))
        timelines[u.id] = pts
        horizon = max(horizon, t)
    import math as _m
    K = int(_m.ceil(horizon / max(delta_tau,1e-6)))
    snaps = {}
    for k in range(K+1):
        tk = k*delta_tau
        pos_k = {}
        for u in inst.uavs:
            pts = timelines[u.id]
            for i in range(len(pts)-1):
                t0, p0 = pts[i]
                t1, p1 = pts[i+1]
                if tk <= t1 or i==len(pts)-2:
                    if t1==t0:
                        pos = p1
                    else:
                        ratio = max(0.0, min(1.0, (tk - t0)/(t1 - t0)))
                        pos = (p0[0] + ratio*(p1[0]-p0[0]), p0[1] + ratio*(p1[1]-p0[1]))
                    pos_k[u.id] = pos
                    break
        snaps[tk] = pos_k
    return snaps
