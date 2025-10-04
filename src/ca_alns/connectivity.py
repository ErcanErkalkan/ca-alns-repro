
import math
from collections import deque, defaultdict
from typing import Dict, Set

def compute_cadence_bound(R: float, rho: float, v_max: float) -> float:
    return max(1e-3, (R - 2.0*rho) / (2.0 * max(v_max, 1e-6)))

def bfs_connected(adj: Dict[int, Set[int]]) -> bool:
    if not adj:
        return True
    nodes = list(adj.keys())
    seen = set([nodes[0]])
    dq = deque([nodes[0]])
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v); dq.append(v)
    return len(seen) == len(nodes)

def build_snapshot_graph(positions: dict, cfg) -> dict:
    """Return adjacency dict[uav_id -> set(neighbors)] using 'range' or 'sinr' from cfg.
    positions: {uav_id: (x,y,alt)}  (alt optional; default=100m)
    cfg: has fields mode ('range'|'sinr'), R, rho, tx_power_dbm, noise_dbm, gamma_th_db, bidirectional
    """
    if getattr(cfg, "mode", "range") == "sinr":
        return snapshot_graph_sinr(positions,
                                   tx_power_dbm=getattr(cfg, "tx_power_dbm", 20.0),
                                   noise_dbm=getattr(cfg, "noise_dbm", -96.0),
                                   gamma_th_db=getattr(cfg, "gamma_th_db", 6.0),
                                   bidirectional=getattr(cfg, "bidirectional", True))
    else:
        # default range with tightened margin (R-ρ)
        R_eff = max(0.0, getattr(cfg, "R", 150.0) - getattr(cfg, "rho", 15.0))
        edges = {u:set() for u in positions}
        ids = list(positions.keys())
        for i,u in enumerate(ids):
            xu,yu,*alt_u = positions[u]
            for v in ids[i+1:]:
                xv,yv,*alt_v = positions[v]
                d = math.hypot(xu-xv, yu-yv)
                if d <= R_eff:
                    edges[u].add(v); edges[v].add(u)
        return edges

def check_connected_surrogate_then_bfs(positions: dict, cfg, surrogate_score: float, tau: float) -> bool:
    """Safety-first connectivity check:
       - If surrogate_score >= tau → 'risky': run exact BFS and return its verdict.
       - If |surrogate_score - tau| < band (implicit): run BFS as well (borderline).
       - Else rely on range/SINR graph.
    """
    adj = build_snapshot_graph(positions, cfg)
    # Borderline band: fixed small band; in real code, read from frozen threshold params
    band = 0.05
    if surrogate_score >= tau or abs(surrogate_score - tau) < band:
        return bfs_connected(adj)
    return bfs_connected(adj)  # we still return BFS to be conservative

# ---- Option A: SINR adjacency (simplified Friis + shadowing hooks) ----

def pathloss_db(d_m: float, n_los=2.1, n_nlos=3.0, los=True, pl0_db=32.4):
    if d_m <= 1.0: 
        return pl0_db
    n = n_los if los else n_nlos
    return pl0_db + 10.0*n*math.log10(d_m)

def rx_power_dbm(tx_power_dbm: float, d_m: float, los=True):
    return tx_power_dbm - pathloss_db(d_m, los=los)

def sinr_db(p_rx_dbm: float, noise_dbm: float, inter_dbm_list=None):
    inter_mw = 0.0
    if inter_dbm_list:
        inter_mw = sum(10**(p/10.0) for p in inter_dbm_list)
    p_mw = 10**(p_rx_dbm/10.0)
    n_mw = 10**(noise_dbm/10.0)
    return 10.0*math.log10(p_mw / max(n_mw + inter_mw, 1e-12))

def snapshot_graph_sinr(positions: dict,
                        tx_power_dbm=20.0,
                        noise_dbm=-96.0,
                        gamma_th_db=6.0,
                        bidirectional=True,
                        altitude_m: float = 100.0):
    ids = list(positions.keys())
    edges = {u:set() for u in ids}
    for i,u in enumerate(ids):
        xu,yu,*_ = positions[u]
        for v in ids[i+1:]:
            xv,yv,*_ = positions[v]
            d = max(1.0, math.hypot(xu-xv, yu-yv))
            # crude LoS decision by distance
            los = d < 500.0
            prx_uv = rx_power_dbm(tx_power_dbm, d, los=los)
            prx_vu = prx_uv  # symmetric here
            sinr_uv = sinr_db(prx_uv, noise_dbm, inter_dbm_list=None)
            sinr_vu = sinr_db(prx_vu, noise_dbm, inter_dbm_list=None)
            ok = (sinr_uv >= gamma_th_db) and (sinr_vu >= gamma_th_db) if bidirectional else ((sinr_uv >= gamma_th_db) or (sinr_vu >= gamma_th_db))
            if ok:
                edges[u].add(v); edges[v].add(u)
    return edges


import numpy as np

def laplacian_lambda2(adj_dict):
    ids = list(adj_dict.keys())
    idx = {u:i for i,u in enumerate(ids)}
    n = len(ids)
    if n == 0:
        return 0.0
    A = np.zeros((n,n), dtype=float)
    for u, nbrs in adj_dict.items():
        for v in nbrs:
            if u in idx and v in idx:
                A[idx[u], idx[v]] = 1.0
                A[idx[v], idx[u]] = 1.0
    d = np.diag(A.sum(axis=1))
    L = d - A
    w = np.linalg.eigvals(L)
    w = np.sort(np.real(w))
    if len(w) < 2:
        return 0.0
    return float(w[1])

def avg_degree(adj_dict):
    if not adj_dict:
        return 0.0
    return float(np.mean([len(v) for v in adj_dict.values()]))

def mst_max_edge_length(positions: dict):
    ids = list(positions.keys())
    if len(ids) <= 1:
        return 0.0
    import math
    edges = []
    for i,u in enumerate(ids):
        (xu,yu) = positions[u]
        for j in range(i+1, len(ids)):
            v = ids[j]; xv,yv = positions[v]
            d = math.hypot(xu-xv, yu-yv)
            edges.append((d,u,v))
    edges.sort()
    parent = {i:i for i in ids}
    rank = {i:0 for i in ids}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def union(a,b):
        ra, rb = find(a), find(b)
        if ra==rb: return False
        if rank[ra]<rank[rb]: parent[ra]=rb
        elif rank[ra]>rank[rb]: parent[rb]=ra
        else: parent[rb]=ra; rank[ra]+=1
        return True
    used = 0
    max_edge = 0.0
    for d,u,v in edges:
        if union(u,v):
            used += 1
            max_edge = max(max_edge, d)
            if used == len(ids)-1:
                break
    return float(max_edge)
