"""Reference points for manually reported field-team starting locations."""

# Most reference points follow the field planner's town dataset. Jizan uses
# the city coordinates published by the Saudi Ministry of Foreign Affairs.
PLANNER_CITY_COORDS = {
    "Riyadh": (24.67296, 46.68938),
    "Jeddah": (21.53674, 39.20804),
    "Makkah": (21.3891, 39.8579),
    "Jizan": (16.883333, 42.55),
    "Abha": (18.2207, 42.5043),
    "Madinah": (24.4672, 39.6111),
    "Dammam": (26.4451, 50.085),
    "Unizah": (26.0941, 43.9735),  # planner reference town: Unayzah
    "Hail": (27.49873, 41.69754),
}

PLANNER_CITY_OPTIONS = "\n".join(PLANNER_CITY_COORDS)
