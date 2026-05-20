import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer

# NEW: Import the OTLP gRPC Exporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def setup_telemetry():
    """Initializes OpenTelemetry tracing and instruments the gRPC server."""
    
    resource = Resource.create({
        "service.name": "solver-service",
        "service.version": "0.1.0",
        "service.environment": os.getenv("ENVIRONMENT", "production")
    })

    provider = TracerProvider(resource=resource)
    
    # ---------------------------------------------------------
    # ENTERPRISE CONFIGURATION: Exporting to OTLP endpoint
    # ---------------------------------------------------------
    # By default, OTLPSpanExporter looks for the environment variable:
    # OTEL_EXPORTER_OTLP_ENDPOINT (which defaults to http://localhost:4317)
    
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    print(f"📡 Routing OpenTelemetry traces to OTLP endpoint: {otlp_endpoint}")
    
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True  # Set to False if your collector requires TLS
    )
    
    # Use BatchSpanProcessor so we don't block the main thread while exporting
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)

    # Automatically intercept and trace incoming gRPC requests
    grpc_instrumentor = GrpcInstrumentorServer()
    grpc_instrumentor.instrument()

    return trace.get_tracer(__name__)
