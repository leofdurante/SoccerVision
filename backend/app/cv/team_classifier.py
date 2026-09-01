"""Team classification via shirt-color clustering.

Deliberately simple and explainable, per spec — no deep-learning
classifier. For each player crop we:

  1. Take the upper third of the bounding box (torso/shirt region,
     avoiding shorts/socks and the grass background below the feet).
  2. Convert to HSV.
  3. Take the dominant hue via a small color histogram (skips near-white/
     near-black/low-saturation pixels, which are usually grass, lines, or
     shadow rather than the shirt itself).

Two-team assignment then clusters all dominant player colors from a
frame (or a batch of frames) into two groups with KMeans. This means
`TeamClassifier` is fit once per analysis job on a representative sample
of crops, then reused to `classify()` each individual crop against the
fitted cluster centers.

Goalkeepers are a known edge case (different-colored kit) and are not
specially handled — they will likely be misclassified or assigned with
low confidence, which is deliberate per spec rather than over-engineered.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from sklearn.cluster import KMeans

logger = logging.getLogger("soccervision.cv.team_classifier")

Team = str  # "home" | "away" | "unknown"


def _dominant_hsv(crop: np.ndarray) -> np.ndarray | None:
    if crop.size == 0:
        return None
    h, w = crop.shape[:2]
    if h < 4 or w < 4:
        return None

    # Upper-body region: skip the top 15% (head/hair) and stop at 55% of
    # height (roughly torso), and trim the outer edges to avoid background.
    top = int(h * 0.15)
    bottom = int(h * 0.55)
    left = int(w * 0.2)
    right = int(w * 0.8)
    torso = crop[top:bottom, left:right]
    if torso.size == 0:
        return None

    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
    pixels = hsv.reshape(-1, 3)

    # Filter out grass/shadow/white-line pixels: low saturation (near
    # gray/white) or very low value (near black/shadow).
    mask = (pixels[:, 1] > 40) & (pixels[:, 2] > 40)
    filtered = pixels[mask]
    if filtered.shape[0] < 10:
        filtered = pixels  # fall back to unfiltered rather than failing

    return np.median(filtered, axis=0)


class TeamClassifier:
    """Fit on a batch of player crops (from one analysis job), then
    classify individual crops against the fitted two-team clusters."""

    def __init__(self, manual_team_colors: dict[str, tuple[int, int, int]] | None = None):
        self._kmeans: KMeans | None = None
        self._label_to_team: dict[int, str] = {}
        self.manual_team_colors = manual_team_colors  # optional HSV fallback: {"home": (h,s,v), "away": (h,s,v)}

    def fit(self, crops: list[np.ndarray]) -> bool:
        samples = []
        for crop in crops:
            hsv = _dominant_hsv(crop)
            if hsv is not None:
                samples.append(hsv)

        if len(samples) < 4:
            logger.warning("Not enough valid shirt-color samples (%d) to fit team clusters", len(samples))
            return False

        X = np.array(samples)
        self._kmeans = KMeans(n_clusters=2, n_init=10, random_state=42).fit(X)

        # Deterministically label clusters "home"/"away" by hue so repeated
        # runs on the same video are stable: lower mean hue -> "home".
        centers = self._kmeans.cluster_centers_
        hue_order = np.argsort(centers[:, 0])
        self._label_to_team = {int(hue_order[0]): "home", int(hue_order[1]): "away"}
        return True

    def classify(self, crop: np.ndarray) -> dict:
        hsv = _dominant_hsv(crop)
        if hsv is None or self._kmeans is None:
            return {"team": "unknown", "confidence": 0.0}

        distances = self._kmeans.transform(hsv.reshape(1, -1))[0]
        closest = int(np.argmin(distances))
        team = self._label_to_team.get(closest, "unknown")

        # Confidence: how much closer the winning cluster is vs. the other,
        # normalized to (0, 1]. Two clusters only, so this is a simple ratio.
        d_win, d_other = sorted(distances)
        confidence = float(d_other / (d_win + d_other)) if (d_win + d_other) > 0 else 0.5

        return {"team": team, "confidence": round(confidence, 3)}
