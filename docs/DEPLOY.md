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
   - `https://hnf.linuxarena.net`
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

    hnf.linuxarena.net  ->  http://hnf-frontend.hnf.svc.cluster.local:80

`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` already include the public name.

### 2b. Direct exposure via traefik-ext (hnf.alcocer.net)

Same pattern as jellyfin: the frontend Ingress is attached to the
`websecure,websecure-ext` Traefik entrypoints, so it is reachable through the
`traefik-external` LoadBalancer as well as the internal one, with the TLS
certificate (`hnf-tls`) issued by `clusterissuer-he` for both names.

Manual step: create the `hnf.alcocer.net` DNS record at he.net (Hurricane
Electric), pointing where the other externally-published `*.alcocer.net`
names (e.g. jellyfin's) point. Remember to add
`https://hnf.alcocer.net` to the Google OAuth client's authorized
JavaScript origins or login will fail on that host.

### 3. Strava (optional — activity auto-import)

Users can link Strava so their workouts (e.g. a Polar watch syncing through
Polar Flow → Strava) are imported automatically.

1. Create an API application at https://www.strava.com/settings/api
   (one per Strava account is allowed; any account can own it):
   - **Authorization Callback Domain**: `hnf.alcocer.net` — must match
     `PUBLIC_BASE_URL` in the ConfigMap.
   - Website/category: anything reasonable.
2. Put the *Client ID* in `deploy/k8s/configmap.yml` → `STRAVA_CLIENT_ID`
   (it is not a secret) and commit.
3. Create the secret with the *Client Secret* by hand (never in the repo):

       kubectl create secret generic hnf-strava -n hnf \
         --from-literal=STRAVA_CLIENT_SECRET=<client secret>

4. Restart the backend to pick both up:

       kubectl rollout restart deployment/hnf-backend -n hnf

While `STRAVA_CLIENT_ID` is empty the integration is hidden in the app.
Users connect from **Perfil → Conexiones**; activities then sync on app open
or via "Sincronizar ahora".

### 4. Admin access

- Django admin: https://hnf.k.alcocer.net/admin — user `m.alcocer1978@gmail.com`,
  password:

      kubectl get secret -n hnf hnf-admin -o jsonpath='{.data.ADMIN_PASSWORD}' | base64 -d

- `hnfctl` (the plan-review CLI):

      export HNF_ADMIN_TOKEN=$(kubectl get secret -n hnf hnf-admin -o jsonpath='{.data.ADMIN_API_TOKEN}' | base64 -d)
      export HNF_API_URL=https://hnf.k.alcocer.net   # or https://hnf.linuxarena.net
      cli/hnfctl pending

  From Claude Code in this repo, the `hnf-plan` skill drives the whole
  review + plan-generation workflow.

## Useful checks

    kustomize build deploy/k8s | kubectl apply --dry-run=client -f -
    argocd app get hnf
    kubectl get pods -n hnf
    kubectl logs -n hnf job/hnf-migrate
