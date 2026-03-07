from __future__ import annotations

import os
from typing import Optional

from loguru import logger


def setup_tracing(service_name: str = "nanobot") -> bool:
    """Initialize OpenTelemetry tracing if enabled via env.

    Control via environment variables (no hard dependency):
      - NANOBOT_TRACING_ENABLED=true            Enable tracing init
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://...  OTLP endpoint
      - OTEL_TRACES_EXPORTER=otlp|console       Exporter selection (default: console if no endpoint)

    Returns True if tracing successfully initialized, else False.
    """
    enabled = os.getenv("NANOBOT_TRACING_ENABLED", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        exporter_name = os.getenv("OTEL_TRACES_EXPORTER", "otlp")

        resource = Resource.create({"service.name": service_name})
        sampler_ratio = float(os.getenv("OTEL_TRACES_SAMPLER_RATIO", "1.0"))
        provider = TracerProvider(resource=resource, sampler=ParentBased(TraceIdRatioBased(sampler_ratio)))

        if endpoint and exporter_name == "otlp":
            exporter = OTLPSpanExporter(endpoint=endpoint.rstrip("/"))
        else:
            # Fallback simple console exporter
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            exporter = ConsoleSpanExporter()
            processor = SimpleSpanProcessor(exporter)
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            logger.info("Tracing enabled with console exporter")
            return True

        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logger.info("Tracing enabled with OTLP exporter: {}", endpoint or "default")
        return True
    except ModuleNotFoundError:
        logger.warning("OpenTelemetry not installed; set extras or install opentelemetry-sdk to enable tracing")
        return False
    except Exception as e:
        logger.error("Tracing init failed: {}", e)
        return False
