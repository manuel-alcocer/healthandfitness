"""Minimal structural validation of a plan document.

The full schema is documented in docs/PLAN_SCHEMA.md; this keeps malformed
submissions from the admin CLI out of the database.
"""

from datetime import date

VALID_SESSION_TYPES = {"walk", "run", "swim", "bike", "gym", "hike", "other", "rest"}


class PlanValidationError(ValueError):
    pass


def _require(condition: bool, message: str):
    if not condition:
        raise PlanValidationError(message)


def validate_plan_data(data: dict) -> None:
    _require(isinstance(data, dict), "plan must be an object")
    for key in ("summary", "daily_calories", "macros", "nutrition", "exercise",
                "weekly_weight_targets"):
        _require(key in data, f"plan.{key} is required")

    _require(isinstance(data["daily_calories"], int) and 800 <= data["daily_calories"] <= 6000,
             "daily_calories out of range")

    macros = data["macros"]
    for key in ("protein_g", "carbs_g", "fat_g"):
        _require(isinstance(macros.get(key), int | float), f"macros.{key} is required")

    nutrition = data["nutrition"]
    meals = nutrition.get("meals")
    _require(isinstance(meals, list) and meals, "nutrition.meals must be a non-empty list")
    for meal in meals:
        _require(isinstance(meal.get("name"), str), "each meal needs a name")
        _require(isinstance(meal.get("options"), list) and meal["options"],
                 f"meal '{meal.get('name')}' needs options")

    exercise = data["exercise"]
    schedule = exercise.get("weekly_schedule")
    _require(isinstance(schedule, list) and schedule,
             "exercise.weekly_schedule must be a non-empty list")
    for session in schedule:
        _require(session.get("day") in (1, 2, 3, 4, 5, 6, 7),
                 "session.day must be 1..7 (1=Monday)")
        _require(session.get("type") in VALID_SESSION_TYPES,
                 f"unknown session type {session.get('type')!r}")

    targets = data["weekly_weight_targets"]
    _require(isinstance(targets, list) and len(targets) >= 2,
             "weekly_weight_targets needs at least start and end points")
    last = None
    for t in targets:
        _require(isinstance(t.get("week"), int), "target.week must be an int")
        d = date.fromisoformat(t["date"])  # raises ValueError on bad format
        _require(last is None or d > last, "weekly_weight_targets dates must be increasing")
        last = d
        _require(isinstance(t.get("weight_kg"), int | float), "target.weight_kg required")
