.PHONY: up down logs ps ramp kill
up:            ## build images and start Airflow + flagd
	docker compose up -d --build
down:          ## stop and remove containers, networks, and volumes
	docker compose down -v
logs:          ## follow the scheduler logs
	docker compose logs -f airflow-scheduler
ps:            ## show container status
	docker compose ps
ramp:          ## set the canary percent, e.g. make ramp PCT=30
	./scripts/ramp.sh $(PCT)
kill:          ## flip the kill switch (canary -> 0%)
	./scripts/ramp.sh 0
