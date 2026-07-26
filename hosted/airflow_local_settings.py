"""Register the OpenFeature backend the Airflow cluster policy reads.

Hosted demo default is Unleash (a real backend with a real admin UI), so a visitor flips the flag /
adjusts the rollout in Unleash and the next DAG parse moves tasks between pools. Set
``OF_BACKEND=flagd`` for the file-based reference backend instead. Airflow imports this at settings
init, in every component (api-server, scheduler, dag-processor).
"""
from __future__ import annotations

import os
import time

from openfeature import api

backend = os.getenv("OF_BACKEND", "unleash")

if backend == "unleash":
    from UnleashClient import UnleashClient

    from openfeature_airflow.providers.unleash import UnleashProvider

    client = UnleashClient(
        url=os.getenv("UNLEASH_URL", "http://unleash:4242/api"),
        app_name="airflow-openfeature",
        custom_headers={"Authorization": os.getenv("UNLEASH_TOKEN", "default:development.unleash-insecure-api-token")},
        refresh_interval=5,
    )
    client.initialize_client()
    # The flag is a boolean toggle gated by a percentage rollout; enabled maps to canary_pool.
    api.set_provider(
        UnleashProvider(client, context_field="userId", enabled_values={"airflow.task.pool": "canary_pool"})
    )
else:
    from openfeature.contrib.provider.flagd import FlagdProvider

    api.set_provider(FlagdProvider(host=os.getenv("OPENFEATURE_FLAGD_HOST", "flagd"), port=8013))

time.sleep(1)  # let the provider connect before the first DAG parse
