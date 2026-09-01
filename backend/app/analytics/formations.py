"""Heuristic formation estimation.

Explicitly NOT a trained classifier (per spec). Outfield players (the
presumed goalkeeper — the single deepest player — is excluded) are
clustered by their depth (field_x, adjusted for attacking direction)
into 3 or 4 "lines" using 1D k-means. Whichever k produces the better
silhouette score is kept. Line sizes, ordered from deepest to most
advanced, are joined into a string like "4-3-3" or "4-2-3-1".

Confidence is a heuristic derived from cluster separation quality, not a
calibrated probability — always returned alongside
`formation_is_heuristic=True` at the API layer so the frontend can label
it honestly.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

Point = tuple[float, float]


def _depth_values(positions: list[Point], team: str) -> list[float]:
    """Depth measured from the team's own goal (higher = further advanced)."""
    return [p[0] if team == "home" else 100 - p[0] for p in positions]


def estimate_formation(positions: list[Point], team: str) -> dict:
    """Returns {"formation": str | None, "confidence": float}."""
    if len(positions) < 4:
        return {"formation": None, "confidence": 0.0}

    depths = sorted(_depth_values(positions, team))
    outfield = depths[1:]  # drop the deepest player (presumed goalkeeper)
    if len(outfield) < 3:
        return {"formation": None, "confidence": 0.0}

    X = np.array(outfield).reshape(-1, 1)

    candidates = []
    for k in (3, 4):
        if len(outfield) <= k:
            continue
        try:
            km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
            labels = km.labels_
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(X, labels)
            candidates.append((score, k, km))
        except Exception:
            continue

    if not candidates:
        return {"formation": None, "confidence": 0.0}

    best_score, best_k, best_km = max(candidates, key=lambda c: c[0])

    # Group outfield depths by cluster, order lines defense -> attack.
    lines: dict[int, list[float]] = {}
    for value, label in zip(outfield, best_km.labels_):
        lines.setdefault(int(label), []).append(value)
    ordered = sorted(lines.items(), key=lambda kv: np.mean(kv[1]))
    line_sizes = [len(v) for _, v in ordered]

    formation = "-".join(str(n) for n in line_sizes)
    # Map silhouette score (-1..1, realistically ~0..0.6 here) to a
    # 0..1 confidence band that doesn't overclaim precision.
    confidence = round(max(0.0, min(1.0, 0.4 + best_score)), 2)

    return {"formation": formation, "confidence": confidence}
