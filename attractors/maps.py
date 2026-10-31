"""
Iterated 2-D maps. Each `step(x, y, p)` takes numpy arrays x, y and a
parameter vector p and returns (x', y'). Everything is vectorised so we
can run thousands of trajectories in lock-step.

Families 1-5 are classics. Family 6 ("fold") is mine; I wanted at least one
map in the search that nobody had looked at before I did.
"""
import numpy as np

sin, cos, tanh = np.sin, np.cos, np.tanh


def clifford(x, y, p):
    a, b, c, d = p
    return sin(a * y) + c * cos(a * x), sin(b * x) + d * cos(b * y)


def dejong(x, y, p):
    a, b, c, d = p
    return sin(a * y) - cos(b * x), sin(c * x) - cos(d * y)


def svensson(x, y, p):
    a, b, c, d = p
    return d * sin(a * x) - sin(b * y), c * cos(a * x) + cos(b * y)


def bedhead(x, y, p):
    a, b = p[:2]
    return sin(x * y / b) * y + cos(a * x - y), x + sin(y) / b


def gumowski_mira(x, y, p):
    a, alpha = p[:2]

    def f(v):
        v2 = v * v
        return a * v + 2.0 * (1.0 - a) * v2 / (1.0 + v2)

    xn = y + alpha * (1.0 - 0.05 * y * y) * y + f(x)
    yn = -x + f(xn)
    return xn, yn


def fold(x, y, p):
    """My own. A Clifford-like skeleton with a radial term, so the map
    'knows' how far from the origin it is and can fold differently near
    the centre than at the edge. The tanh keeps it bounded."""
    a, b, c, d, e = p
    r = np.sqrt(x * x + y * y)
    xn = sin(a * y) + c * cos(a * x) + e * tanh(r) * cos(b * r)
    yn = sin(b * x) + d * cos(b * y) + e * tanh(r) * sin(a * r)
    return xn, yn


# name -> (step function, parameter ranges as (lo, hi) per parameter)
FAMILIES = {
    "clifford": (clifford, [(-3, 3), (-3, 3), (-1.6, 1.6), (-1.6, 1.6)]),
    "dejong": (dejong, [(-3, 3), (-3, 3), (-3, 3), (-3, 3)]),
    "svensson": (svensson, [(-3, 3), (-3, 3), (-3, 3), (-3, 3)]),
    "bedhead": (bedhead, [(-1, 1), (-1, 1)]),
    "gumowski_mira": (gumowski_mira, [(-1, 1), (-0.05, 0.05)]),
    "fold": (fold, [(-3, 3), (-3, 3), (-1.6, 1.6), (-1.6, 1.6), (-1.2, 1.2)]),
}


def sample_params(name, rng):
    _, ranges = FAMILIES[name]
    p = np.array([rng.uniform(lo, hi) for lo, hi in ranges])
    if name == "bedhead":
        # b near zero blows up
        while abs(p[1]) < 0.2:
            p[1] = rng.uniform(-1, 1)
    return p
