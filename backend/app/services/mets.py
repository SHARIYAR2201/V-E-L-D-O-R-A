"""MET seed table.

Values are transcribed from the 2011 Compendium of Physical Activities (Ainsworth et al., 2011) for a
small set of common activities so the app works out of the box. They MUST be verified against
https://pacompendium.com/ and can be replaced wholesale with `python -m scripts.ingest --met-file <csv>`
(columns: key,category,name,met,code).
"""
SEED = [
    ("walk_slow", "walking", "Walking, ~2.0 mph, slow", 2.8),
    ("walk_moderate", "walking", "Walking, ~3.0 mph, moderate", 3.5),
    ("walk_brisk", "walking", "Walking, ~3.5 mph, brisk", 4.3),
    ("walk_fast", "walking", "Walking, ~4.0 mph, very brisk", 5.0),
    ("run_5mph", "running", "Running, 5 mph (12 min/mile)", 8.3),
    ("run_6mph", "running", "Running, 6 mph (10 min/mile)", 9.8),
    ("run_7mph", "running", "Running, 7 mph (8.5 min/mile)", 11.0),
    ("run_8mph", "running", "Running, 8 mph (7.5 min/mile)", 11.8),
    ("cycle_leisure", "cycling", "Bicycling, <10 mph, leisure", 4.0),
    ("cycle_moderate", "cycling", "Bicycling, 12-13.9 mph, moderate", 8.0),
    ("cycle_vigorous", "cycling", "Bicycling, 14-15.9 mph, vigorous", 10.0),
    ("swim_light", "swimming", "Swimming laps, light/moderate effort", 5.8),
    ("swim_vigorous", "swimming", "Swimming laps, vigorous effort", 9.8),
    ("strength_moderate", "gym", "Resistance (weight) training, light/moderate", 3.5),
    ("strength_vigorous", "gym", "Resistance (weight) training, vigorous", 6.0),
    ("circuit", "gym", "Circuit training, general", 8.0),
    ("rowing_moderate", "cardio", "Rowing machine, moderate effort", 7.0),
    ("elliptical", "cardio", "Elliptical trainer, moderate effort", 5.0),
    ("jump_rope", "cardio", "Rope jumping, moderate pace", 11.8),
    ("yoga", "mind-body", "Yoga, Hatha", 2.5),
    ("basketball", "sports", "Basketball, game", 8.0),
    ("soccer", "sports", "Soccer, casual", 7.0),
    ("tennis", "sports", "Tennis, singles", 8.0),
]
