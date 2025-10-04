
"""MILP small-instance reference with lazy connectivity cuts (skeleton).
Requires pulp (or ortools) installed to solve; here we define model-building functions.
"""
try:
    import pulp
except Exception as e:
    pulp = None

def build_small_milp(coords, uav_count: int, R_eff: float):
    if pulp is None:
        raise RuntimeError("pulp not available; install pulp to use MILP reference.")
    n = len(coords)
    prob = pulp.LpProblem("UAV_Routing_Connectivity", pulp.LpMinimize)
    # Edge vars y_uv
    y = pulp.LpVariable.dicts("y", ((i,j) for i in range(n) for j in range(n) if i!=j), 0, 1, cat=pulp.LpBinary)
    # Objective: minimize total distance (simple)
    import math
    def dist(i,j):
        a,b = coords[i], coords[j]
        return math.hypot(a[0]-b[0], a[1]-b[1])
    prob += pulp.lpSum(dist(i,j)*y[(i,j)] for i in range(n) for j in range(n) if i!=j)

    # Degree constraints (simple TSP-like)
    for i in range(n):
        prob += pulp.lpSum(y[(i,j)] for j in range(n) if j!=i) == 1
        prob += pulp.lpSum(y[(j,i)] for j in range(n) if j!=i) == 1

    # Lazy connectivity cuts would be added via solver callbacks; pulp does not expose callbacks uniformly.
    # As a placeholder, one can iteratively solve, find disconnected UAV snapshot graph, and add cuts.

    return prob, y
