"""Offline regional road-time estimates for the Field Planner.

Town-to-town road times come from the bundled OSRM/OpenStreetMap matrix. Local
legs use the planner's existing straight-line circuity and speed assumptions.
This is a planning estimate, not live routing or traffic.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

from sig_warehouse.sig_warehouse import field_planner as fp


MATRIX_VERSION = "ksa-30-towns-osrm-2026-10-27-v1"
MATRIX_FILE = Path(__file__).with_name("field_planner_town_mesh.json")
NEARBY_DIRECT_KM = 75.0
MAX_MESH_POINTS_PER_END = 2
MAX_PHYSICAL_SPEED_KMH = 130.0


def _load_matrix():
    with MATRIX_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema") != "sig-field-planner-town-mesh/v1":
        raise ValueError("town mesh schema is unsupported")
    towns = data["towns"]
    durations = data["durations_seconds"]
    distances = data["distances_meters"]
    names = [str(town["name"]) for town in towns]
    if len(names) != 30 or len(set(names)) != len(names):
        raise ValueError("town mesh must contain 30 unique towns")
    if len(durations) != len(names) or len(distances) != len(names):
        raise ValueError("town mesh matrix dimensions do not match towns")
    for matrix in (durations, distances):
        if any(len(row) != len(names) for row in matrix):
            raise ValueError("town mesh matrix is not square")
        for row in matrix:
            for value in row:
                if value is not None and (not math.isfinite(float(value)) or float(value) < 0):
                    raise ValueError("town mesh contains an invalid route measure")
    points = []
    for town in towns:
        lat, lon = float(town["lat"]), float(town["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("town mesh contains an invalid coordinate")
        points.append((lat, lon))
    version = str(data.get("matrix_version") or "")
    if not version:
        raise ValueError("town mesh is missing its version")
    return names, points, durations, distances, version


try:
    _TOWN_NAMES, _TOWN_POINTS, _DURATIONS, _DISTANCES, MATRIX_VERSION = _load_matrix()
    _TOWN_INDEX = {name: i for i, name in enumerate(_TOWN_NAMES)}
    MATRIX_AVAILABLE = True
except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
    _TOWN_NAMES, _TOWN_POINTS, _DURATIONS, _DISTANCES, _TOWN_INDEX = [], [], [], [], {}
    MATRIX_VERSION = ""
    MATRIX_AVAILABLE = False


def _nearest_towns(point, count=MAX_MESH_POINTS_PER_END):
    return sorted(range(len(_TOWN_POINTS)),
                  key=lambda i: fp.haversine_km(point, _TOWN_POINTS[i]))[:count]


@lru_cache(maxsize=8192)
def _estimate_cached(origin, destination, circuity, speed_kmh):
    """Estimate one directed between-trip leg; coordinates are rounded cache keys."""
    direct_km = fp.haversine_km(origin, destination)
    legacy_km = direct_km * circuity
    legacy_hours = legacy_km / speed_kmh
    base = {"hours": legacy_hours, "km": legacy_km, "method": "legacy_direct",
            "origin_towns": [], "destination_towns": [], "fallback_reason": ""}
    if not MATRIX_AVAILABLE:
        base["fallback_reason"] = "matrix_unavailable"
        return base
    if direct_km <= NEARBY_DIRECT_KM:
        base["fallback_reason"] = "within_direct_radius"
        return base

    origin_towns = _nearest_towns(origin)
    destination_towns = _nearest_towns(destination)
    if not origin_towns or not destination_towns:
        base["fallback_reason"] = "no_reference_town"
        return base
    if origin_towns[0] == destination_towns[0]:
        base["origin_towns"] = [_TOWN_NAMES[i] for i in origin_towns]
        base["destination_towns"] = [_TOWN_NAMES[i] for i in destination_towns]
        base["fallback_reason"] = "same_nearest_town"
        return base

    best = None
    for i in origin_towns:
        local_origin_km = fp.haversine_km(origin, _TOWN_POINTS[i]) * circuity
        for j in destination_towns:
            if i == j:
                continue
            middle_seconds = _DURATIONS[i][j]
            middle_meters = _DISTANCES[i][j]
            if middle_seconds is None or middle_meters is None:
                continue
            local_destination_km = fp.haversine_km(_TOWN_POINTS[j], destination) * circuity
            local_hours = (local_origin_km + local_destination_km) / speed_kmh
            road_hours = float(middle_seconds) / 3600.0
            total_hours = local_hours + road_hours
            total_km = local_origin_km + float(middle_meters) / 1000.0 + local_destination_km
    # Keep the estimate physically plausible. A valid road route can be longer
    # than the old straight-line approximation; preferring that approximation
    # would systematically understate difficult/indirect journeys.
            total_hours = max(total_hours, direct_km / MAX_PHYSICAL_SPEED_KMH)
            candidate = (total_hours, total_km, i, j, local_hours, road_hours)
            if best is None or candidate[0] < best[0]:
                best = candidate
    if best is None:
        base["fallback_reason"] = "no_matrix_pair"
        return base
    return {"hours": best[0], "km": best[1], "method": "town_mesh",
            "origin_towns": [_TOWN_NAMES[i] for i in origin_towns],
            "destination_towns": [_TOWN_NAMES[i] for i in destination_towns],
            "hub_pair": [_TOWN_NAMES[best[2]], _TOWN_NAMES[best[3]]],
            "local_hours": best[4], "matrix_hours": best[5], "fallback_reason": ""}


def estimate(origin, destination, params):
    """Return modeled km/hours and provenance for a between-trip movement."""
    origin = (round(float(origin[0]), 5), round(float(origin[1]), 5))
    destination = (round(float(destination[0]), 5), round(float(destination[1]), 5))
    circuity = float(params["circuity"])
    speed_kmh = float(params["speed_kmh"])
    if speed_kmh <= 0 or circuity <= 0:
        raise ValueError("travel speed and circuity must be positive")
    return dict(_estimate_cached(origin, destination, circuity, speed_kmh))


def clear_cache():
    _estimate_cached.cache_clear()
