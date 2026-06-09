import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from purview_mcp.infrastructure.config.settings import Settings

logger = structlog.get_logger(__name__)

_SERVICE_NAME = "purview-mcp-server"


def configure_telemetry(settings: Settings) -> TracerProvider | None:
    """Set up OTLP trace export when OTEL_ENABLED is true.

    Returns the provider so the caller can flush spans on shutdown, or None
    when telemetry is disabled (the OpenTelemetry API stays a no-op).
    """
    if not settings.otel_enabled:
        return None

    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint or None)
    provider = TracerProvider(resource=Resource.create({"service.name": _SERVICE_NAME}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    logger.info("purview_mcp.otel.enabled", endpoint=settings.otel_exporter_otlp_endpoint)
    return provider
