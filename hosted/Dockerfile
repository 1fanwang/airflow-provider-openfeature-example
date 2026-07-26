ARG AIRFLOW_VERSION=2.11.0

# flagd binary from the official distroless image.
FROM ghcr.io/open-feature/flagd:latest AS flagd

FROM apache/airflow:${AIRFLOW_VERSION}

USER root
COPY --from=flagd /flagd-build /usr/local/bin/flagd
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Bake in everything the demo needs.
COPY --chown=airflow:0 hosted/webserver_config.py /opt/airflow/webserver_config.py
COPY --chown=airflow:0 config/ /opt/airflow/config/
COPY --chown=airflow:0 dags/ /opt/airflow/dags/
COPY --chown=airflow:0 flags/ /opt/airflow/flags/
COPY --chown=airflow:0 hosted/entrypoint.sh /entrypoint.sh

USER root
RUN chmod +x /entrypoint.sh
USER airflow

ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor \
    AIRFLOW__CORE__LOAD_EXAMPLES=false \
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false \
    AIRFLOW__OPENFEATURE__ENABLE_POLICY=True \
    AIRFLOW__WEBSERVER__EXPOSE_CONFIG=false \
    AIRFLOW__CORE__FERNET_KEY=ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=

ENTRYPOINT ["/entrypoint.sh"]
