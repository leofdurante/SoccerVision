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
video into two groups with KMeans — unless the coach named the kits, in
which case each crop is matched to those two colours and anyone who
matches neither (refs, coaches, fans) is `unknown` and can be dropped.

Goalkeepers in a different-coloured kit are a known edge case: with
named kits they will look like staff and be filtered out.
"""

from __future__ import annotations

import logging
import re

import cv2
import numpy as np
from sklearn.cluster import KMeans

logger = logging.getLogger("soccervision.cv.team_classifier")

Team = str  # "home" | "away" | "unknown"

_HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")

# Combined HSV distance above this means "not either kit". 0.35 is about
# 30–35° of hue when saturation matches: enough slack for lighting, tight
# enough that a black jacket or a green steward bib misses both kits.
MAX_KIT_DISTANCE = 0.35


def parse_hex_to_hsv(hex_color: str) -> tuple[int, int, int]:
    """'#rrggbb' or 'rrggbb' → OpenCV HSV (H 0–179, S/V 0–255)."""
    raw = hex_color.strip()
    if not _HEX_RE.match(raw):
        raise ValueError(f"Not a hex colour: {hex_color!r}")
    raw = raw[1:] if raw.startswith("#") else raw
    r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    bgr = np.uint8([[[b, g, r]]])
    h, s, v = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0, 0]
    return int(h), int(s), int(v)


def hsv_distance(a: np.ndarray | tuple, b: np.ndarray | tuple) -> float:
    """0 = identical, ~1 = opposite. Hue wraps; white/black ignore hue."""
    h1, s1, v1 = [float(x) for x in a]
    h2, s2, v2 = [float(x) for x in b]
    achromatic = s1 < 45 and s2 < 45
    if achromatic:
        return 0.5 * abs(v1 - v2) / 255.0 + 0.5 * abs(s1 - s2) / 255.0
    if s1 < 45 or s2 < 45:
        return 0.55 + 0.45 * abs(v1 - v2) / 255.0
    dh = min(abs(h1 - h2), 180.0 - abs(h1 - h2)) / 90.0
    ds = abs(s1 - s2) / 255.0
    dv = abs(v1 - v2) / 255.0
    return 0.65 * dh + 0.20 * ds + 0.15 * dv


def _shirt_hsv(crop: np.ndarray) -> np.ndarray | None:
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

    # Chromatic pixels first (grass/lines/shadows are low-S or low-V). If
    # the kit is white or black there aren't enough of those, so fall back
    # to the full torso — otherwise white shirts would be invisible.
    chromatic = pixels[(pixels[:, 1] > 40) & (pixels[:, 2] > 40)]
    sample = chromatic if chromatic.shape[0] >= 10 else pixels
    if sample.shape[0] < 10:
        return None
    return np.median(sample, axis=0)


# Back-compat name used by tests that imported the old helper via classify.
_dominant_hsv = _shirt_hsv


class TeamClassifier:
    """Fit on a batch of player crops (from one analysis job), then
    classify individual crops against the fitted two-team clusters.

    Pass `manual_team_colors` as HSV triples keyed by "home"/"away" to
    skip KMeans and match shirts to the kits the coach picked.
    """

    def __init__(self, manual_team_colors: dict[str, tuple[int, int, int]] | None = None):
        self._kmeans: KMeans | None = None
        self._label_to_team: dict[int, str] = {}
        self.manual_team_colors = manual_team_colors

    @property
    def filters_non_kit(self) -> bool:
        return bool(self.manual_team_colors) and len(self.manual_team_colors) >= 2

    def fit(self, crops: list[np.ndarray]) -> bool:
        if self.filters_non_kit:
            return True

        samples = []
        for crop in crops:
            hsv = _shirt_hsv(crop)
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
        hsv = _shirt_hsv(crop)
        if hsv is None:
            return {"team": "unknown", "confidence": 0.0}

        if self.filters_non_kit:
            return self._classify_against_kits(hsv)

        if self._kmeans is None:
            return {"team": "unknown", "confidence": 0.0}

        distances = self._kmeans.transform(hsv.reshape(1, -1))[0]
        closest = int(np.argmin(distances))
        team = self._label_to_team.get(closest, "unknown")

        d_win, d_other = sorted(distances)
        confidence = float(d_other / (d_win + d_other)) if (d_win + d_other) > 0 else 0.5
        return {"team": team, "confidence": round(confidence, 3)}

    def _classify_against_kits(self, hsv: np.ndarray) -> dict:
        dists = {
            team: hsv_distance(hsv, color)
            for team, color in (self.manual_team_colors or {}).items()
        }
        best_team = min(dists, key=dists.get)
        best_d = dists[best_team]
        others = [d for team, d in dists.items() if team != best_team]
        other_d = min(others) if others else 1.0

        if best_d > MAX_KIT_DISTANCE:
            return {"team": "unknown", "confidence": round(max(0.0, 1.0 - best_d), 3)}

        confidence = float(other_d / (best_d + other_d)) if (best_d + other_d) > 0 else 0.5
        return {"team": best_team, "confidence": round(confidence, 3)}
