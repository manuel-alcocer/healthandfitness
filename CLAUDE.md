# CLAUDE.md

Health & Fitness (hnf): weight-goal + exercise tracking app.
Django 6 backend (`backend/`), React 19 + Vite frontend (`frontend/`),
deployed to the armlab k8s cluster via ArgoCD (namespace `hnf`).

## Commands

- Backend tests: `cd backend && uv run pytest`
- Backend dev server: `cd backend && uv run python manage.py runserver`
- Frontend dev: `cd frontend && npm run dev` (proxies /api to :8000)
- Frontend build check: `cd frontend && npm run build`
- Full stack locally: `docker compose up --build`

## Conventions

- All code, comments and commit messages in English; UI copy in Spanish.
- Conventional commits (`feat:`, `fix:`, ...). Do not push without confirmation.
- Images are built by CI (`.github/workflows/release.yml`); never edit the
  `newTag` values in `deploy/k8s/kustomization.yml` by hand — CI owns them.

## Attending users (admin workflow)

Use the `hnf-plan` skill (`.claude/skills/hnf-plan/SKILL.md`) to review
pending users and generate their nutrition + exercise plans through
`cli/hnfctl`. The plan JSON schema lives in `docs/PLAN_SCHEMA.md` and is
validated by `hnfctl submit-plan`.
