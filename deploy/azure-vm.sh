#!/usr/bin/env bash
# Provision the always-on hosted demo on Azure: a small VM running the compose stack behind Caddy.
#
# Prereqs: `az login` to the target subscription (a personal one, not work infra), Docker not needed
# locally (the image is built in ACR). Run from the repo root:  bash deploy/azure-vm.sh
set -euo pipefail

RG=${RG:-of-demo}
LOC=${LOC:-eastus}
ACR=${ACR:-ofdemo$(openssl rand -hex 4)}
DNS=${DNS:-ofopenfeature$(openssl rand -hex 3)}
FQDN="$DNS.$LOC.cloudapp.azure.com"
ADMIN_PASSWORD=${ADMIN_PASSWORD:-$(openssl rand -base64 15 | tr -d '/+=' | head -c 16)}
UNLEASH_ADMIN_PASSWORD=${UNLEASH_ADMIN_PASSWORD:-$(openssl rand -base64 15 | tr -d '/+=' | head -c 16)}
SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 24)}

echo ">> resource group + registry"
az group create -n "$RG" -l "$LOC" -o none
az acr create -g "$RG" -n "$ACR" --sku Basic --admin-enabled true -o none

echo ">> build the image in ACR (cloud build, amd64)"
az acr build -r "$ACR" -t of-demo:next -f hosted/Dockerfile . -o none

echo ">> VM (B2ms, 2 vCPU / 8 GB) + open 80/443"
az vm create -g "$RG" -n of-demo-vm --image Ubuntu2204 --size Standard_B2ms \
  --storage-sku StandardSSD_LRS --admin-username azureuser --generate-ssh-keys \
  --public-ip-sku Standard --public-ip-address-dns-name "$DNS" -o none
az vm open-port -g "$RG" -n of-demo-vm --port 80 --priority 900 -o none
az vm open-port -g "$RG" -n of-demo-vm --port 443 --priority 901 -o none

echo ">> deliver the stack and bring it up (via run-command; SSH is often restricted)"
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PW=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)
B_COMPOSE=$(base64 < docker-compose.hosted.yml)
B_CADDY=$(base64 < hosted/Caddyfile)
B_SETUP=$(base64 < hosted/setup_unleash.sh)
B_FLAGS=$(base64 < flags/flags.json)

SCRIPT=$(cat <<OUTER
set -e
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
mkdir -p /opt/demo/hosted /opt/demo/flags && cd /opt/demo
echo '$B_COMPOSE' | base64 -d > docker-compose.hosted.yml
echo '$B_CADDY'   | base64 -d > hosted/Caddyfile
echo '$B_SETUP'   | base64 -d > hosted/setup_unleash.sh
echo '$B_FLAGS'   | base64 -d > flags/flags.json
cat > .env <<ENV
OF_IMAGE=$ACR.azurecr.io/of-demo:next
SITE_ADDRESS=$FQDN
BASE_URL=https://$FQDN
HTTP_PORT=80
ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$SECRET_KEY
UNLEASH_ADMIN_PASSWORD=$UNLEASH_ADMIN_PASSWORD
ENV
docker login $ACR.azurecr.io -u $ACR_USER -p '$ACR_PW'
docker compose -f docker-compose.hosted.yml --env-file .env pull -q
docker compose -f docker-compose.hosted.yml --env-file .env up -d
OUTER
)
az vm run-command invoke -g "$RG" -n of-demo-vm --command-id RunShellScript \
  --scripts "$SCRIPT" -o none

cat <<DONE

  Demo is coming up (Caddy needs ~30s for its cert).
    Airflow : https://$FQDN            login viewer / viewer   (read-only)
    Unleash : https://$FQDN/unleash    login admin  / $UNLEASH_ADMIN_PASSWORD
    Airflow admin: admin / $ADMIN_PASSWORD

  Flip the airflow.task.pool rollout in the Unleash UI and watch the pools change in Airflow.
  Tear down with:  az group delete -n $RG --yes --no-wait
DONE
