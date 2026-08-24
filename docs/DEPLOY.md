# Deployment

Everything is GitOps: push to `main` → GitHub Actions builds the multi-arch
images and bumps `deploy/k8s/kustomization.yml` → ArgoCD (Application `hnf`,
registered from k8s-home-apps `deployments/hnf.yml`) syncs the `hnf`
namespace.

Secrets (Django SECRET_KEY, DB password, admin token/password) are generated
in-cluster by External Secrets Operator Password generators; nothing secret
lives in this repo. The database is a role + database on the shared
PostgreSQL (`postgresql.databases.svc.cluster.local`), created by the
`hnf-db-init` Sync hook.

## One-time setup

### 1. Google Sign-In (required for user login)

1. Go to https://console.cloud.google.com/apis/credentials (any project).
2. *Create credentials → OAuth client ID → Web application*, name `hnf`.
3. Authorized JavaScript origins:
   - `https://hnf.alcocer.net`
   - `https://hnf.k.alcocer.net`
   - `http://localhost:5173` (dev)
   (No redirect URIs needed: the app uses the Google Identity Services popup.)
4. Copy the client ID into `GOOGLE_CLIENT_ID` in
   `deploy/k8s/configmap.yml`, commit and push. Restart happens on sync;
   if pods were already running: `kubectl rollout restart deploy -n hnf hnf-backend`.
   The client ID is public, not a secret — the backend only uses it to verify
   Google-signed ID tokens.

### 2. Cloudflare Tunnel (public URL)

In the Cloudflare Zero Trust dashboard, add a public hostname to the tunnel:

    hnf.alcocer.net  ->  http://hnf-frontend.hnf.svc.cluster.local:80

`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` already include the public name.

### 3. Admin access

- Django admin: https://hnf.k.alcocer.net/admin — user `m.alcocer1978@gmail.com`,
  password:

      kubectl get secret -n hnf hnf-admin -o jsonpath='{.data.ADMIN_PASSWORD}' | base64 -d

- `hnfctl` (the plan-review CLI):

      export HNF_ADMIN_TOKEN=$(kubectl get secret -n hnf hnf-admin -o jsonpath='{.data.ADMIN_API_TOKEN}' | base64 -d)
      export HNF_API_URL=https://hnf.k.alcocer.net   # or https://hnf.alcocer.net
      cli/hnfctl pending

  From Claude Code in this repo, the `hnf-plan` skill drives the whole
  review + plan-generation workflow.

## Useful checks

    kustomize build deploy/k8s | kubectl apply --dry-run=client -f -
    argocd app get hnf
    kubectl get pods -n hnf
    kubectl logs -n hnf job/hnf-migrate
