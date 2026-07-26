# Deploy the hosted demo

The stack in `docker-compose.hosted.yml` is the whole thing: real Apache Airflow 3.3.0 with the
OpenFeature provider, a real [Unleash](https://www.getunleash.io/) backend and its admin UI, and
`flagd` as the no-UI reference backend, all behind [Caddy](https://caddyserver.com/) (automatic
HTTPS). Change the rollout in the Unleash UI at `/unleash` and tasks move between pools in the
Airflow UI at `/`. No DAG code changes.

## What a visitor sees

- `/` — the Airflow UI. Airflow 3.x serves it through the api-server and requires a login; the demo
  ships a read-only `viewer` / `viewer` account. (Airflow 2.x allowed anonymous `AUTH_ROLE_PUBLIC`;
  the 3.x UI does not, so a shared read-only login is the substitute.)
- `/unleash` — the real Unleash admin UI. Log in as `admin` / `$UNLEASH_ADMIN_PASSWORD`, open the
  `airflow.task.pool` flag, and change the rollout percentage or toggle it off. Within a few seconds
  the provider picks it up, the next DAG parse re-runs the policy, and the split changes.

## Run it on any Docker host

```bash
SITE_ADDRESS=:80 docker compose -f docker-compose.hosted.yml up -d --build
```

Open <http://localhost>. For a public host with HTTPS, point a domain at the machine and set
`SITE_ADDRESS=your.domain` (Caddy fetches a Let's Encrypt cert) and `BASE_URL=https://your.domain`.
Set real values for `ADMIN_PASSWORD`, `UNLEASH_ADMIN_PASSWORD`, and `SECRET_KEY`.

## Azure (always-on VM)

`deploy/azure-vm.sh` provisions a `Standard_B2ms` VM (2 vCPU / 8 GB, ~$60/mo), builds the image in
ACR, opens 80/443, and brings the stack up behind Caddy. Set the variables at the top (or accept the
generated defaults) after `az login` to the target subscription, then run it. It prints the public
URL and the generated passwords at the end.

## Security note

Exposing the Unleash admin UI lets visitors change flags — that is the point of the demo, and the
flag change is self-healing (rebuild to reset). Do not point this stack at anything that matters, and
always set a strong `UNLEASH_ADMIN_PASSWORD`. A full feature-flag admin console is not something to
run unauthenticated on the public internet.
