"""Point OpenFeature at the flagd backend so the placement policy can read flags.

The policy ships with the provider and auto-registers on the ``airflow.policy`` entry point. It stays
off until ``AIRFLOW__OPENFEATURE__ENABLE_POLICY=True`` (set in docker-compose.yml). This file is the one
piece of platform wiring: register the backend. Airflow imports it at settings init, in every component.
"""

from __future__ import annotations

import os
import time

from openfeature import api
from openfeature.contrib.provider.flagd import FlagdProvider

# Default to the "flagd" compose service; the single-container hosted image sets
# OPENFEATURE_FLAGD_HOST=localhost since flagd runs beside Airflow in that case.
host = os.getenv("OPENFEATURE_FLAGD_HOST", "flagd")
port = int(os.getenv("OPENFEATURE_FLAGD_PORT", "8013"))
api.set_provider(FlagdProvider(host=host, port=port))
time.sleep(1)  # let the gRPC resolver connect before the first DAG parse
