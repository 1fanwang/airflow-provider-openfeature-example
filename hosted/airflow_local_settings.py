"""Register the OpenFeature backend the Airflow cluster policy reads.

Hosted demo default is Unleash (a real backend with a real admin UI), so a visitor flips the flag /
adjusts the rollout in Unleash and the next DAG parse moves tasks between pools. Set
``OF_BACKEND=flagd`` for the file-based reference backend instead.

The Unleash client is created lazily: Airflow 3.x's LocalExecutor forks task workers, and an
``UnleashClient`` started here would run background polling threads in the forking parent, which
deadlocks the child (fork + threads -> SIGKILL). Deferring ``initialize_client()`` to first use means
the forking parent has no client threads; the dag-processor and each task worker start their own after
they are already their own process.
"""
from __future__ import annotations

import os
import time

from openfeature import api

backend = os.getenv("OF_BACKEND", "unleash")

if backend == "unleash":
    from UnleashClient import UnleashClient

    from openfeature_airflow.providers.unleash import UnleashProvider

    class LazyUnleashClient:
        """Duck-typed UnleashClient that connects on first evaluation, not at import (fork-safe)."""

        def __init__(self, **kwargs) -> None:
            self._kwargs = kwargs
            self._client: UnleashClient | None = None

        def _ensure(self) -> UnleashClient:
            if self._client is None:
                self._client = UnleashClient(**self._kwargs)
                self._client.initialize_client()
                time.sleep(1)  # let the first fetch land before we read
            return self._client

        def is_enabled(self, *args, **kwargs):
            return self._ensure().is_enabled(*args, **kwargs)

        def get_variant(self, *args, **kwargs):
            return self._ensure().get_variant(*args, **kwargs)

    client = LazyUnleashClient(
        url=os.getenv("UNLEASH_URL", "http://unleash:4242/unleash/api"),
        app_name="airflow-openfeature",
        custom_headers={"Authorization": os.getenv("UNLEASH_TOKEN", "default:development.unleash-insecure-api-token")},
        refresh_interval=5,
    )
    api.set_provider(
        UnleashProvider(client, context_field="userId", enabled_values={"airflow.task.pool": "canary_pool"})
    )
else:
    from openfeature.contrib.provider.flagd import FlagdProvider

    api.set_provider(FlagdProvider(host=os.getenv("OPENFEATURE_FLAGD_HOST", "flagd"), port=8013))
    time.sleep(1)
