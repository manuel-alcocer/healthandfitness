# Plan document schema

The plan a goal carries (`Plan.data`) is a single JSON document. It is
validated structurally by `backend/apps/plans/schema.py` on submission
through the admin API.

```jsonc
{
  "summary": "One-sentence description of the plan (Spanish, shown to the user).",
  "daily_calories": 1800,                     // int, 800..6000
  "macros": { "protein_g": 120, "carbs_g": 180, "fat_g": 55 },
  "nutrition": {
    "guidelines": ["General nutrition rules (Spanish)"],
    "meals": [
      {
        "name": "Desayuno",                   // used as the key for meal logging
        "time": "08:00",                      // optional
        "options": ["Option A", "Option B"]   // >= 1 concrete meal options
      }
    ]
  },
  "exercise": {
    "guidelines": ["Warm-up rules, safety notes (Spanish)"],
    "weekly_schedule": [
      {
        "day": 1,                             // 1=Monday .. 7=Sunday, one entry per day
        "type": "walk",                       // walk|run|swim|bike|gym|hike|other|rest
        "title": "Caminata rápida",           // shown to the user
        "target": {                           // all optional, only what applies
          "distance_km": 5,
          "duration_min": 60,
          "hr_zone": "Z2",
          "pace_min_km": "7:00"
        },
        "details": "Free-text instructions (Spanish)"
      }
    ]
  },
  "weekly_weight_targets": [
    // The expected weight curve, week 0 (start) through the goal date.
    // Dates strictly increasing; the dashboard interpolates between points.
    { "week": 0, "date": "2026-08-24", "weight_kg": 92.0 },
    { "week": 1, "date": "2026-08-31", "weight_kg": 91.4 }
  ]
}
```

## Submission wrapper (admin API / `hnfctl submit-plan`)

```jsonc
{
  "feasibility": "realistic",        // or "unrealistic"
  "message": "Coach's message to the user (Spanish).",
  "plan": { ...plan document... },
  // Only when unrealistic — the plan above must be built FOR this suggestion:
  "suggested_goal": { "target_weight_kg": 82.0, "target_date": "2027-01-15" }
}
```

- `realistic` → the goal becomes `active` and the plan is visible immediately.
- `unrealistic` → the goal becomes `suggested`; the user sees the message and
  the alternative goal, and can accept it (plan activates) or resubmit a new
  goal.
