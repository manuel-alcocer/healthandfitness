# Health & Fitness (hnf)

Personal weight-goal and exercise planning platform. Users sign in with their
Google account, enter their biometric data and a weight goal with a target
date, and wait for the admin to review it. The admin generates a personalized
nutrition + exercise plan from the Claude Code CLI (see `cli/` and
`.claude/skills/hnf-plan/`). From then on the user logs weigh-ins, workouts
(distance, heart rate, pace...) and meal adherence, and the app tells them
whether they are on track, with progress charts.

Public URL: https://hnf.alcocer.net (via Cloudflare Tunnel).
Internal URL: https://hnf.k.alcocer.net.

## Architecture

| Piece      | Stack                                                        |
|------------|--------------------------------------------------------------|
| `backend/` | Django 6 + DRF + SimpleJWT, PostgreSQL, Google Sign-In       |
| `frontend/`| React 19 + Vite + TypeScript, Recharts, mobile-first         |
| `cli/`     | `hnfctl` – admin CLI that talks to the private admin API     |
| `deploy/`  | Kustomize manifests for the k8s cluster (multi-arch images)  |
| `argocd/`  | ArgoCD Application (referenced from k8s-home-apps)           |

The frontend pod (nginx-unprivileged) serves the built SPA and proxies
`/api`, `/admin` and `/static` to the backend, so the browser only ever sees
one origin.

## User flow

1. User signs in with Google, fills in biometrics and a goal → status `pending`.
2. Admin runs `hnfctl pending` / uses the `hnf-plan` Claude Code skill,
   reviews the request and submits a plan:
   - realistic goal → plan attached, goal becomes `active`;
   - unrealistic goal → goal becomes `suggested` with an explanation and an
     alternative goal + plan the user can accept with one tap.
3. User logs daily data; `/api/progress` computes adherence and weight-trend
   versus the plan's weekly targets and the dashboard says whether they are
   on track.

## Local development

```bash
# backend (SQLite by default)
cd backend && uv sync && uv run python manage.py migrate && uv run python manage.py runserver
# frontend
cd frontend && npm install && npm run dev
# full stack with PostgreSQL
docker compose up --build
```

Tests: `cd backend && uv run pytest`.

## Deployment

Push to `main` → GitHub Actions builds multi-arch images (amd64 + arm64) to
GHCR and bumps `deploy/k8s/kustomization.yml` → ArgoCD syncs the `hnf`
namespace. See `docs/DEPLOY.md` for the one-time setup (Google OAuth client,
Cloudflare tunnel, admin token retrieval).
