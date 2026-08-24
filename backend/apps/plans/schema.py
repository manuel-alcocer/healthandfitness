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

    def _check_meals(meals, where):
        _require(isinstance(meals, list) and meals, f"{where} must be a non-empty list")
        for meal in meals:
            _require(isinstance(meal.get("name"), str), f"each meal in {where} needs a name")
            _require(isinstance(meal.get("options"), list) and meal["options"],
                     f"meal '{meal.get('name')}' in {where} needs options")

    # Preferred shape: a weekly menu with different dishes each day.
    # Legacy shape (same meals every day): nutrition.meals.
    menu = nutrition.get("weekly_menu")
    if menu is not None:
        _require(isinstance(menu, list) and len(menu) == 7,
                 "nutrition.weekly_menu must have exactly 7 entries")
        _require(sorted(d.get("day") for d in menu) == [1, 2, 3, 4, 5, 6, 7],
                 "weekly_menu days must be exactly 1..7")
        for entry in menu:
            _check_meals(entry.get("meals"), f"weekly_menu day {entry.get('day')}")
    else:
        _check_meals(nutrition.get("meals"), "nutrition.meals")

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
