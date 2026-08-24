export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  avatar_url: string;
  is_staff: boolean;
}

export interface Profile {
  sex: "M" | "F";
  birth_date: string;
  height_cm: number;
  initial_weight_kg: string;
  activity_level: "sedentary" | "light" | "moderate" | "active" | "very_active";
  resting_hr: number | null;
  body_fat_pct: string | null;
  waist_cm: number | null;
  hip_cm: number | null;
  health_conditions: string;
  dietary_preferences: string;
  training_days_per_week: number;
  preferred_activities: string[];
  equipment: string;
  age: number;
  bmi: number;
}

export type GoalStatus = "pending" | "active" | "suggested" | "completed" | "cancelled";

export interface Goal {
  id: number;
  target_weight_kg: string;
  target_date: string;
  motivation: string;
  status: GoalStatus;
  revision_requested: boolean;
  revision_note: string;
  admin_message: string;
  suggested_target_weight_kg: string | null;
  suggested_target_date: string | null;
  reviewed_at: string | null;
  start_weight_kg: string;
  start_date: string;
  created_at: string;
  has_plan: boolean;
}

export interface Me {
  user: User;
  profile: Profile | null;
  goal: Goal | null;
}

export interface PlanSession {
  day: number;
  type: string;
  title?: string;
  target?: {
    distance_km?: number;
    duration_min?: number;
    hr_zone?: string;
    pace_min_km?: string;
    [k: string]: unknown;
  };
  details?: string;
}

export interface PlanMeal {
  name: string;
  time?: string;
  options: string[];
}

export interface PlanData {
  summary: string;
  daily_calories: number;
  macros: { protein_g: number; carbs_g: number; fat_g: number };
  nutrition: { guidelines?: string[]; meals: PlanMeal[] };
  exercise: { guidelines?: string[]; weekly_schedule: PlanSession[] };
  weekly_weight_targets: { week: number; date: string; weight_kg: number }[];
}

export interface Plan {
  id: number;
  goal_id: number;
  start_date: string;
  created_at: string;
  data: PlanData;
}

export interface Progress {
  state: "no_active_goal" | "active";
  goal?: {
    start_weight_kg: number;
    target_weight_kg: number;
    start_date: string;
    target_date: string;
  };
  weight_series?: { date: string; weight_kg: number }[];
  expected_series?: { date: string; weight_kg: number }[];
  streak_days?: number;
  weight?: {
    current_kg: number | null;
    expected_today_kg: number | null;
    delta_kg: number | null;
    status: "on_track" | "ahead" | "behind" | "no_data" | "no_plan";
    lost_kg: number | null;
    to_go_kg: number | null;
  };
  exercise_week?: {
    week_start: string;
    sessions_planned: number;
    sessions_done: number;
    distance_planned_km: number;
    distance_done_km: number;
    minutes_done: number;
    compliance: number | null;
  };
  nutrition_week?: { days_logged: number; adherence: number | null };
  verdict?: { status: "on_track" | "at_risk" | "off_track" | "no_data"; message: string };
  weekly_exercise?: { week_start: string; sessions: number; distance_km: number; minutes: number }[];
}

export interface WeightEntry {
  id: number;
  date: string;
  weight_kg: string;
  body_fat_pct: string | null;
  notes: string;
}

export interface ActivityEntry {
  id: number;
  date: string;
  activity_type: string;
  title: string;
  duration_min: number;
  distance_km: string | null;
  avg_hr: number | null;
  max_hr: number | null;
  avg_speed_kmh: string | null;
  elevation_m: number | null;
  calories: number | null;
  perceived_effort: number | null;
  plan_day: number | null;
  notes: string;
}

export interface MealLog {
  name: string;
  status: "full" | "partial" | "skipped";
  option?: string;
}

export interface NutritionEntry {
  id: number;
  date: string;
  meals: MealLog[];
  calories_estimate: number | null;
  water_l: string | null;
  notes: string;
  adherence: number | null;
}

export type DayLevel = "none" | "red" | "yellow" | "green" | "medal";

export interface CalendarDay {
  date: string;
  level: DayLevel;
  score?: number;
  nutrition_adherence?: number | null;
  planned?: string | null;
  exercise_ratio?: number | null;
  activities?: number;
}

export interface CalendarMonth {
  year: number;
  month: number;
  today: string;
  tracked_from: string | null;
  medals: number;
  days: CalendarDay[];
}

export const ACTIVITY_LABELS: Record<string, string> = {
  walk: "Andar",
  run: "Correr",
  swim: "Nadar",
  bike: "Bici",
  gym: "Gimnasio",
  hike: "Senderismo",
  other: "Otro",
  rest: "Descanso",
};

export const DAY_NAMES = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"];
