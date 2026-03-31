from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from packages.core.config import Settings

logger = logging.getLogger(__name__)


def configure_observability(settings: Settings) -> None:
    resource = Resource(attributes={"service.name": "infrasentinel"})
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-untyped]
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTLP exporter configured: %s", settings.otel_exporter_otlp_endpoint)
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp-proto-grpc not installed; "
                "install with: uv sync --extra observability"
            )
        except Exception as exc:
            logger.warning("Failed to configure OTLP exporter: %s", exc)

    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse.opentelemetry import LangfuseSpanExporter  # type: ignore[import-untyped]

            langfuse_exporter = LangfuseSpanExporter(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(langfuse_exporter))
            logger.info("Langfuse exporter configured: %s", settings.langfuse_host)
        except ImportError:
            logger.warning(
                "langfuse not installed; install with: uv sync --extra observability"
            )
        except Exception as exc:
            logger.warning("Failed to configure Langfuse exporter: %s", exc)
