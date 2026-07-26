"""Point OpenFeature at the flagd backend so the placement policy can read flags.

The policy ships with the provider and auto-registers on the ``airflow.policy`` entry point. It stays
off until ``AIRFLOW__OPENFEATURE__ENABLE_POLICY=True`` (set in docker-compose.yml). This file is the one
piece of platform wiring: register the backend. Airflow imports it at settings init, in every component.
"""

from __future__ import annotations

import time

from openfeature import api
from openfeature.contrib.provider.flagd import FlagdProvider

api.set_provider(FlagdProvider(host="flagd", port=8013))
time.sleep(1)  # let the gRPC resolver connect before the first DAG parse
