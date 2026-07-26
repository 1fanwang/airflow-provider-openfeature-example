ARG AIRFLOW_VERSION=3.3.0

# flagd binary (kept as the no-UI reference backend; Unleash is the primary UI backend).
FROM ghcr.io/open-feature/flagd:latest AS flagd

FROM apache/airflow:${AIRFLOW_VERSION}
ARG AIRFLOW_VERSION

USER root
COPY --from=flagd /flagd-build /usr/local/bin/flagd
USER airflow

# FAB auth manager (roles + anonymous Viewer) under Airflow's own constraints, then the provider
# with the flagd + Unleash backends.
RUN pip install --no-cache-dir "apache-airflow-providers-fab" \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.12.txt"
RUN pip install --no-cache-dir "airflow-provider-openfeature[flagd,unleash]==0.1.0" "openfeature-provider-flipt"

COPY --chown=airflow:0 hosted/webserver_config.py /opt/airflow/webserver_config.py
COPY --chown=airflow:0 hosted/airflow_local_settings.py /opt/airflow/config/airflow_local_settings.py
COPY --chown=airflow:0 dags/ /opt/airflow/dags/
COPY --chown=airflow:0 flags/ /opt/airflow/flags/
COPY --chown=airflow:0 plugins/ /opt/airflow/plugins/

ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor \
    AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager \
    AIRFLOW__CORE__LOAD_EXAMPLES=false \
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false \
    AIRFLOW__OPENFEATURE__ENABLE_POLICY=True \
    OF_BACKEND=unleash
