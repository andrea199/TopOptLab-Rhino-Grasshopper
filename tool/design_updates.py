# SPDX-License-Identifier: GPL-3.0-or-later
"""Projected-gradient updates for signed self-weight compliance derivatives."""
import numpy as np


def project_budget(v, weights, budget, low, high):
    """Euclidean projection onto box bounds and weights @ x == budget."""
    if budget < weights@low-1e-9 or budget > weights@high+1e-9:
        raise ValueError('Self-weight fixed-volume budget is incompatible with Keep/density bounds')
    def trial(lam): return np.clip(v-lam*weights, low, high)
    left, right = -1., 1.
    while weights@trial(left) < budget: left *= 2
    while weights@trial(right) > budget: right *= 2
    for _ in range(90):
        mid = (left+right)/2
        if weights@trial(mid) > budget: left = mid
        else: right = mid
    return trial((left+right)/2)


def projected_candidate(model, x, gradient, step=1, move=.15):
    scale = max(float(np.max(abs(gradient))), 1e-30)
    low = np.maximum(.001, x-move); high = np.minimum(1., x+move)
    return project_budget(x-step*gradient/scale, model.dv, model.design_budget, low, high)


def projected_stationarity(model, x, gradient):
    return float(np.max(abs(projected_candidate(model, x, gradient, move=1)-x)))


def self_weight_step(model, x, response, evaluate):
    """Preserve the material budget; Armijo search using the exact load derivative.
    OC's square-root rule assumes negative sensitivities and is not valid here.
    A failed search is reported explicitly, never labelled as convergence.
    """
    gradient = response['gradient']; step = 1.
    for _ in range(22):
        candidate = projected_candidate(model, x, gradient, step)
        delta = candidate-x
        if np.max(abs(delta)) < 1e-12: return x.copy()
        slope = float(gradient@delta)
        trial, _ = evaluate(model.density(candidate))
        if slope < 0 and trial['compliance'] <= response['compliance']+1e-4*slope:
            return candidate
        step *= .5
    return None
