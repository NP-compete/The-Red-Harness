"""OpenTelemetry configuration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OtelExporterConfig(BaseModel):
    """OTLP exporter connection settings."""

    endpoint: str = Field(default="http://localhost:4317")
    insecure: bool = False


class OtelMetricsConfig(BaseModel):
    """Metric export settings."""

    export_interval_ms: int = Field(default=5000, ge=1000, le=60000)


class OtelTracingConfig(BaseModel):
    """Distributed tracing settings."""

    fastapi_auto_instrument: bool = True


class OtelFileConfig(BaseModel):
    """Top-level OTEL configuration from observability.yaml ``otel:`` section."""

    enabled: bool = False
    exporter: OtelExporterConfig = Field(default_factory=OtelExporterConfig)
    metrics: OtelMetricsConfig = Field(default_factory=OtelMetricsConfig)
    tracing: OtelTracingConfig = Field(default_factory=OtelTracingConfig)
