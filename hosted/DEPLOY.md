# Deploy the demo as a public, read-only, always-on instance

The container in `hosted/` runs the whole demo (Airflow + flagd + a live-activity loop) and serves the
UI read-only to anonymous visitors (`AUTH_ROLE_PUBLIC=Viewer`); a maintainer logs in with `ADMIN_PASSWORD`.
It needs a Postgres. Pick one path.

## Azure (recommended if you have credits)

### Option A: a small VM running compose (simplest)

```bash
az group create -n of-demo -l eastus
az vm create -n of-demo -g of-demo --image Ubuntu2204 --size Standard_B2s \
  --admin-username azureuser --generate-ssh-keys --public-ip-sku Standard
az vm open-port -g of-demo -n of-demo --port 8080

# then on the VM:
#   curl -fsSL https://get.docker.com | sh
#   git clone https://github.com/1fanwang/airflow-provider-openfeature-example.git && cd airflow-provider-openfeature-example
#   ADMIN_PASSWORD=<pick-one> docker compose -f hosted/docker-compose.hosted.yml up -d --build
# open http://<vm-public-ip>:8080  (anonymous = read-only)
```

A `Standard_B2s` (2 vCPU / 4 GB) is about $30/mo, well inside the credit.

### Option B: Azure Container Apps (managed, no VM)

```bash
az group create -n of-demo -l eastus
az postgres flexible-server create -g of-demo -n of-demo-db --public-access 0.0.0.0 \
  --admin-user airflow --admin-password '<db-password>' --tier Burstable --sku-name Standard_B1ms
az containerapp up -n of-demo -g of-demo --source . --ingress external --target-port 8080 \
  --env-vars "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://airflow:<db-password>@of-demo-db.postgres.database.azure.com/airflow?sslmode=require" "ADMIN_PASSWORD=<pick-one>"
# set the app's min replicas to 1 so it never scales to zero (always-on):
az containerapp update -n of-demo -g of-demo --min-replicas 1
```

## Render (paid: ~$7/mo always-on, free sleeps)

The repo ships a `render.yaml` blueprint. Render dashboard -> New -> Blueprint -> pick the repo -> Apply.

## Any Docker host (Oracle Always Free, a Pi, your laptop)

```bash
ADMIN_PASSWORD=<pick-one> docker compose -f hosted/docker-compose.hosted.yml up -d --build
```

## After it's up

- Public URL serves the Airflow UI read-only. The activity loop ramps the flag and triggers the DAGs
  every few minutes, so visitors always see a live canary split across the pools.
- Log in as `admin` / `ADMIN_PASSWORD` to drive it yourself.
- Put it behind a domain and HTTPS with your host's ingress (Azure/Render do this for you).
