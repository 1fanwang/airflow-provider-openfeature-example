ARG AIRFLOW_VERSION=2.11.0
FROM apache/airflow:${AIRFLOW_VERSION}

# Install the provider (from PyPI) plus the flagd OpenFeature backend.
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
