---
name: hnf-plan
description: Attend Health & Fitness users — review pending weight goals, judge feasibility, and generate their personalized nutrition + exercise plan through hnfctl. Use when the user says "atiende a los usuarios", "revisa pendientes", "genera el plan de <user>", or mentions hnf-plan.
---

# Attending Health & Fitness users

You are acting as the coach's assistant. Manuel decides WHO to attend; you
generate the plan with your own judgment. All user-facing text (messages,
plan content) is in **Spanish**; be warm, direct and encouraging, never
clinical or judgmental.

## Workflow

1. `cli/hnfctl pending` — list users waiting for review.
2. For the chosen user: `cli/hnfctl show <id>` — the bundle includes profile,
   derived metrics (age, BMI, BMR, TDEE via Mifflin-St Jeor) and the goal.
3. Judge feasibility (rules below). Discuss briefly with Manuel if borderline.
4. Write the submission JSON (schema: `docs/PLAN_SCHEMA.md`, skeleton:
   `cli/hnfctl template`) to a temp file.
5. `cli/hnfctl submit-plan <id> <file>` — the CLI reports the new goal status.

`hnfctl` needs `HNF_ADMIN_TOKEN` (and `HNF_API_URL` if not production).
Get the token from the cluster:
`kubectl get secret -n hnf hnf-admin -o jsonpath='{.data.ADMIN_API_TOKEN}' | base64 -d`

## Feasibility rules

Compute the implied rate: `(current_weight - target_weight) / weeks_to_target`.

Realistic (weight loss) when ALL hold:
- Rate ≤ 1.0 kg/week AND ≤ 1% of body weight/week (0.3–0.7 is the sweet spot).
- Target weight keeps BMI ≥ 18.5 (compute from height).
- No health conditions in the profile that the plan cannot accommodate.

Otherwise mark `unrealistic` and build a `suggested_goal`: keep the user's
target weight if it is healthy but extend the date to a ~0.5–0.7 kg/week rate
(round to whole weeks); if the target weight itself is unhealthy, raise it to
BMI ≥ 20. The `message` must explain WHY kindly and concretely (health risk,
muscle loss, rebound) and what you propose instead. The plan you attach must
be built for the SUGGESTED goal, not the original.

Weight-gain goals: same logic with ≤ 0.5 kg/week gain.

## Plan quality bar

- **Calories**: TDEE (in the bundle's `derived`) minus 300–600 kcal for loss
  (never below BMR or below 1200 F / 1500 M); plus 200–400 for gain.
- **Macros**: protein 1.6–2.2 g/kg of target weight; fat ≥ 0.6 g/kg; rest carbs.
- **Meals**: ALWAYS use `nutrition.weekly_menu` (7 entries, day 1..7) — the
  dishes must **change through the week** like a real menú semanal; a single
  daily template repeated every day is exactly what the user complained
  about. 3–5 meals per day matching `dietary_preferences` (respect allergies
  and dislikes — never include an excluded food), with **2–4 concrete
  Spanish/mediterranean options per meal per day**, simple to cook. Across
  the week, rotate protein sources (legumbres 2-3 días, pescado blanco y azul
  3-4, huevo, aves, carne roja magra ≤2) and cooking styles (plancha, horno,
  guiso, ensalada, crema). Align with training: more carbs the day of the
  long session. The user uses the menu to plan the week's shopping.
- **Exercise**: exactly 7 entries (day 1..7), sessions on
  `training_days_per_week` days, rest on the others. Use ONLY activities from
  `preferred_activities` and available `equipment`. Progressive volume,
  realistic targets for the profile (an unfit beginner does not start with
  10 km runs). Include HR zones when `resting_hr` is present (Karvonen:
  max HR ≈ 220 − age).
- **weekly_weight_targets**: one point per week from week 0 (today, current
  weight) to the target date. Slightly front-loaded is fine (water weight),
  linear otherwise; last point = target weight on the target date.
- Adapt to `health_conditions` (e.g. knee injury → swim/bike over run).

## Plan revisions

`hnfctl pending` also lists users with an ACTIVE goal marked `+revision`:
they changed the exercise they are willing to do (new `preferred_activities`
/ `training_days_per_week` in the profile) and asked for an updated plan.
The goal's `revision_note` says why — read it and honor it.

For a revision, rebuild the plan for the SAME goal but from where the user is
NOW: current weight = latest entry in `recent_weights` (fall back to
`start_weight_kg`), remaining time = today → `target_date`, and the NEW
activity preferences. `weekly_weight_targets` restarts at week 0 = today with
the current weight. Re-check feasibility for the REMAINING stretch: if it is
no longer healthy, submit as `unrealistic` with a `suggested_goal` (usually
the same target weight with a later date). Submit with `feasibility:
realistic` otherwise — the goal stays active, the plan is replaced, and the
`message` should acknowledge what changed («He cambiado tus sesiones de
carrera por natación, como pediste»).

## Follow-up reviews

`cli/hnfctl progress <id>` shows the same verdict the user sees. Use it when
Manuel asks how someone is doing; suggest plan adjustments if they are
consistently `behind` (smaller deficit rarely helps — check adherence first).

## Days are independent (no weekly cycle)

Submitting a plan materializes its weekly template into one `PlanDay` per
date. After that the template is dead weight: **to change a specific date use
`hnfctl set-day <id> <date> FILE`** (`{"meals": [...]}` and/or
`{"session": {...}}` — session shaped like a `weekly_schedule` entry without
`day`). It changes ONLY that date. `hnfctl days <id> --from A --to B` lists
what each date holds. Resubmitting a full plan regenerates today onwards and
keeps past days as they were.

## Weekly feedback

After reviewing a user's week (typically Monday, for the Mon-Sun just
ended), publish the coach's summary with `hnfctl submit-feedback <id> FILE`:
`{week_start (that Monday), summary (Spanish, warm, concrete numbers),
stats: {weight_delta_kg, distance_km, active_days, nutrition_adherence},
adjustments: [plan changes applied, in Spanish]}`. It appears in the app's
"Entrenador" tab. Pair it with the actual plan edits (`set-day` /
`submit-plan`) so the adjustments listed are real.
