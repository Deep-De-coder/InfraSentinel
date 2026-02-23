from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from packages.core.config import Settings


def configure_observability(settings: Settings) -> None:
    resource = Resource(attributes={"service.name": "infrasentinel"})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    # OTLP exporter wiring intentionally left as a minimal extension point.
    if settings.otel_exporter_otlp_endpoint:
        # Hook point for adding OTLP exporter setup.
        pass
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        # Hook point for optional Langfuse integration.
        pass
