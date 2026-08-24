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
- **Meals**: 3–5 meals matching `dietary_preferences` (respect allergies and
  dislikes — never include an excluded food); 2+ concrete Spanish-food options
  per meal (mediterranean staples, simple to cook).
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

## Follow-up reviews

`cli/hnfctl progress <id>` shows the same verdict the user sees. Use it when
Manuel asks how someone is doing; suggest plan adjustments if they are
consistently `behind` (smaller deficit rarely helps — check adherence first).
